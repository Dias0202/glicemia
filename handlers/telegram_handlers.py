# handlers/telegram_handlers.py
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from services.calculator_service import calculate_total_dose
from services.chart_service import generate_glucose_chart
from services.portion_service import parse_quantity, calculate_carbs_from_portion, format_portion_help
from services.alert_service import format_metabolic_summary, format_glucose_status
from repositories.logs_repository import insert_glycemic_log, get_recent_logs, get_logs_for_period
from repositories.user_repository import upsert_user_profile, get_user_profile
from repositories.food_repository import search_food, get_food_by_id
from repositories.meal_repository import save_meal, get_saved_meals

# --- ESTADOS DO ONBOARDING ---
(AGE, WEIGHT, HEIGHT, HBA1C, BASAL_DOSE, BASAL_TIME,
 ICR, CORRECTION_FACTOR, TARGET_GLUCOSE) = range(9)

# --- ESTADOS DO REGISTRO ---
(REG_GLUCOSE, REG_FOOD_CHOICE, REG_FOOD_SEARCH, REG_FOOD_SELECT,
 REG_FOOD_QTY, REG_FOOD_MORE, REG_MOOD, REG_EXERCISE,
 REG_INSULIN, REG_SAVE_MEAL_CHOICE, REG_SAVE_MEAL_NAME,
 REG_MEAL_SELECT) = range(9, 21)

# --- ESTADOS DO SENSOR ---
(SENSOR_EMAIL, SENSOR_PASSWORD, SENSOR_REGION) = range(21, 24)

# --- ESTADOS DO DIGITAL TWIN ---
(TWIN_FOOD_SEARCH, TWIN_FOOD_SELECT, TWIN_FOOD_QTY, TWIN_MORE) = range(24, 28)

TEXT_FILTER = filters.TEXT & ~filters.COMMAND
VOICE_FILTER = filters.VOICE | filters.AUDIO
PHOTO_FILTER = filters.PHOTO


# =====================================================================
# MENU PRINCIPAL (/start)
# =====================================================================

def _main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Registrar Glicemia", callback_data="cmd_registrar")],
        [
            InlineKeyboardButton("📊 Historico", callback_data="cmd_historico"),
            InlineKeyboardButton("📈 Grafico", callback_data="cmd_grafico"),
        ],
        [
            InlineKeyboardButton("🔍 Buscar Alimento", callback_data="cmd_buscar"),
            InlineKeyboardButton("👤 Meu Perfil", callback_data="cmd_perfil"),
        ],
        [
            InlineKeyboardButton("🩸 Sensor CGM", callback_data="cmd_sensor"),
            InlineKeyboardButton("🔮 Simular", callback_data="cmd_simular"),
        ],
        [
            InlineKeyboardButton("💯 Score Metabolico", callback_data="cmd_score"),
            InlineKeyboardButton("❓ Ajuda", callback_data="cmd_ajuda"),
        ],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    profile = get_user_profile(user.id)

    # Status da glicemia se tiver sensor conectado
    glucose_status = ""
    if profile:
        recent = get_recent_logs(user.id, limit=1)
        if recent:
            last_glucose = recent[0].get("glucose_level")
            trend = recent[0].get("trend_arrow", "")
            if last_glucose:
                glucose_status = f"\n\n{format_glucose_status(last_glucose, trend)}"

    text = (
        f"Ola, {user.first_name}! Eu sou o GlycemiBot.\n"
        "Sua plataforma de inteligencia metabolica.\n"
        f"{glucose_status}\n\n"
        "O que deseja fazer?"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=_main_menu_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=_main_menu_keyboard())


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler de botoes do menu principal."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cmd_historico":
        await _show_historico(query, context)
    elif data == "cmd_grafico":
        await _show_grafico(query, context)
    elif data == "cmd_ajuda":
        await _show_ajuda(query)
    elif data == "cmd_buscar":
        await query.edit_message_text("Digite o nome do alimento que deseja buscar:")
    elif data == "cmd_score":
        await _show_metabolic_score(query, context)
    elif data == "cmd_menu":
        await start(update, context)


# =====================================================================
# AJUDA
# =====================================================================

async def _show_ajuda(query) -> None:
    text = (
        "🤖 GlycemiBot - Plataforma Metabolica\n\n"
        "📋 REGISTRO:\n"
        "  Glicemia → Alimentos → Porcao → Humor →\n"
        "  Exercicio → Calculo de dose → Salvar refeicao\n\n"
        "🩸 SENSOR CGM:\n"
        "  Conecte seu FreeStyle Libre 2 Plus\n"
        "  Monitoramento automatico + alertas proativos\n\n"
        "📸 FOTO DE REFEICAO:\n"
        "  Envie uma foto do prato durante o registro\n"
        "  e a IA identifica os alimentos automaticamente\n\n"
        "🎤 VOZ:\n"
        "  Envie audio em qualquer etapa do registro\n\n"
        "🔮 SIMULACAO (Gemeo Digital):\n"
        "  Simule o impacto de uma refeicao na glicemia\n"
        "  antes de comer\n\n"
        "💯 SCORE METABOLICO:\n"
        "  Pontuacao 0-100 baseada em tempo no alvo,\n"
        "  variabilidade e seguranca\n\n"
        "📊 CALCULO DE DOSE:\n"
        "  Bolus = carbs / ICR\n"
        "  Correcao = (glic - alvo) / FC\n"
        "  Exercicio: Leve -10%, Moderado -20%, Intenso -30%\n\n"
        "📏 MEDIDAS ACEITAS:\n"
        "  200g, 2 colheres de sopa, 1 xicara,\n"
        "  1 concha, 3 fatias, 1 unidade, 1 copo"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Voltar ao menu", callback_data="cmd_menu")]])
    await query.edit_message_text(text, reply_markup=kb)


# =====================================================================
# SCORE METABOLICO
# =====================================================================

async def _show_metabolic_score(query, context) -> None:
    user_id = query.from_user.id
    logs = get_logs_for_period(user_id, days=1)

    if not logs:
        logs = get_logs_for_period(user_id, days=7)

    try:
        from ml_engine.prediction_service import calculate_metabolic_score
        profile = get_user_profile(user_id)
        target = profile.get("target_glucose", 120) if profile else 120
        score_data = calculate_metabolic_score(logs, target_glucose=target)
        text = format_metabolic_summary(score_data)
    except Exception as e:
        logging.error(f"Erro score metabolico: {e}")
        text = "Erro ao calcular score metabolico."

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Voltar ao menu", callback_data="cmd_menu")]])
    await query.edit_message_text(text, reply_markup=kb)


# =====================================================================
# HISTORICO
# =====================================================================

async def _show_historico(query, context) -> None:
    user_id = query.from_user.id
    logs = get_recent_logs(user_id, limit=10)

    if not logs:
        text = "Nenhum registro encontrado."
    else:
        lines = ["📋 Ultimos registros:\n"]
        for log in logs:
            ts = log.get("timestamp", "")[:16].replace("T", " ")
            glucose = log.get("glucose_level", "-")
            carbs = log.get("carbs_ingested", "-")
            bolus = log.get("bolus_insulin", "-")
            refeicao = log.get("refeicao", "-")
            mood = log.get("mood", "")
            exercise = log.get("exercise_intensity", "")
            source = log.get("source_type", "MANUAL")
            trend = log.get("trend_arrow", "")

            source_icon = "🩸" if "LIBRE" in source else "✍️"
            extra = ""
            if mood:
                extra += f" | {mood}"
            if exercise and exercise != "nenhum":
                extra += f" | 🏃 {exercise}"
            if trend:
                extra += f" {trend}"

            lines.append(
                f"  {source_icon} {ts}\n"
                f"  Glic: {glucose} | Carbs: {carbs}g | Ins: {bolus}U\n"
                f"  {refeicao}{extra}\n"
            )
        text = "\n".join(lines)

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Voltar ao menu", callback_data="cmd_menu")]])
    await query.edit_message_text(text, reply_markup=kb)


# =====================================================================
# GRAFICO
# =====================================================================

async def _show_grafico(query, context) -> None:
    user_id = query.from_user.id
    logs = get_logs_for_period(user_id, days=7)

    if not logs:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Voltar ao menu", callback_data="cmd_menu")]])
        await query.edit_message_text("Sem registros nos ultimos 7 dias.", reply_markup=kb)
        return

    try:
        chart_buf = generate_glucose_chart(logs)
        await query.message.reply_photo(photo=chart_buf, caption="📈 Historico glicemico - 7 dias")
        await query.delete_message()
    except Exception as e:
        logging.error(f"Erro ao gerar grafico: {e}")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Voltar ao menu", callback_data="cmd_menu")]])
        await query.edit_message_text("Erro ao gerar grafico.", reply_markup=kb)


# =====================================================================
# BUSCAR ALIMENTO (standalone)
# =====================================================================

async def buscar_alimento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query_text = " ".join(context.args) if context.args else ""
    if not query_text:
        await update.message.reply_text("Use: /buscar <alimento>\nExemplo: /buscar arroz")
        return

    results = search_food(query_text, limit=5)
    if not results:
        await update.message.reply_text(f"Nenhum resultado para '{query_text}'.")
        return

    lines = [f"🔍 Resultados para '{query_text}':\n"]
    for item in results:
        lines.append(f"  {item['food_name']}\n  {item['carbs_per_portion']}g carbs por 100g\n")
    await update.message.reply_text("\n".join(lines))


# =====================================================================
# FLUXO DE ONBOARDING (/perfil)
# =====================================================================

async def start_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "👤 Vamos configurar seu perfil clinico.\n\nQual a sua idade?"
        )
    else:
        await update.message.reply_text(
            "👤 Vamos configurar seu perfil clinico.\n\nQual a sua idade?"
        )
    return AGE


async def _extract_text(update, context):
    """Extrai texto de mensagem de texto ou voz."""
    if update.message.voice or update.message.audio:
        from services.voice_service import transcribe_telegram_voice
        voice = update.message.voice or update.message.audio
        text = await transcribe_telegram_voice(voice, context)
        if text:
            await update.message.reply_text(f"🎤 Entendi: \"{text}\"")
            return text
        await update.message.reply_text("Nao consegui entender o audio. Tente digitar.")
        return None
    return update.message.text


async def ask_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _extract_text(update, context)
    if not text:
        return AGE
    try:
        context.user_data['age'] = int(text.strip().split()[0])
        await update.message.reply_text("Qual o seu peso atual (em kg)?")
        return WEIGHT
    except (ValueError, IndexError):
        await update.message.reply_text("Insira um numero inteiro para a idade.")
        return AGE


async def ask_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _extract_text(update, context)
    if not text:
        return WEIGHT
    try:
        context.user_data['weight'] = float(text.replace(',', '.').split()[0])
        await update.message.reply_text("Qual a sua altura (em metros, ex: 1.75)?")
        return HEIGHT
    except (ValueError, IndexError):
        await update.message.reply_text("Formato invalido.")
        return WEIGHT


async def ask_hba1c(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _extract_text(update, context)
    if not text:
        return HEIGHT
    try:
        context.user_data['height'] = float(text.replace(',', '.').split()[0])
        await update.message.reply_text("Qual sua ultima hemoglobina glicada (HbA1c)?")
        return HBA1C
    except (ValueError, IndexError):
        await update.message.reply_text("Formato invalido.")
        return HEIGHT


async def ask_basal_dose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _extract_text(update, context)
    if not text:
        return HBA1C
    try:
        context.user_data['last_hba1c'] = float(text.replace(',', '.').split()[0])
        await update.message.reply_text("Quantas unidades de insulina BASAL voce aplica por dia?")
        return BASAL_DOSE
    except (ValueError, IndexError):
        await update.message.reply_text("Formato invalido.")
        return HBA1C


async def ask_basal_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _extract_text(update, context)
    if not text:
        return BASAL_DOSE
    try:
        context.user_data['basal_dose'] = float(text.replace(',', '.').split()[0])
        await update.message.reply_text("Horario da insulina basal (ex: 22:00)?")
        return BASAL_TIME
    except (ValueError, IndexError):
        await update.message.reply_text("Formato invalido.")
        return BASAL_DOSE


async def ask_icr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _extract_text(update, context)
    if not text:
        return BASAL_TIME
    context.user_data['basal_time'] = text.strip()
    await update.message.reply_text(
        "Qual sua RAZAO INSULINA/CARBOIDRATO (ICR)?\n\n"
        "Quantos gramas de carbo 1U de insulina rapida cobre?\n"
        "Ex: se 1U cobre 10g, digite 10."
    )
    return ICR


async def ask_correction_factor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _extract_text(update, context)
    if not text:
        return ICR
    try:
        context.user_data['icr'] = float(text.replace(',', '.').split()[0])
        await update.message.reply_text(
            "Qual seu FATOR DE CORRECAO (FC)?\n\n"
            "Quantos mg/dL 1U de rapida reduz sua glicemia?\n"
            "Ex: se 1U abaixa 50 mg/dL, digite 50."
        )
        return CORRECTION_FACTOR
    except (ValueError, IndexError):
        await update.message.reply_text("Formato invalido. Insira um numero.")
        return ICR


async def ask_target_glucose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _extract_text(update, context)
    if not text:
        return CORRECTION_FACTOR
    try:
        context.user_data['correction_factor'] = float(text.replace(',', '.').split()[0])
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("100", callback_data="target_100"),
                InlineKeyboardButton("110", callback_data="target_110"),
                InlineKeyboardButton("120", callback_data="target_120"),
            ]
        ])
        await update.message.reply_text("Qual sua GLICEMIA ALVO (mg/dL)?", reply_markup=kb)
        return TARGET_GLUCOSE
    except (ValueError, IndexError):
        await update.message.reply_text("Formato invalido.")
        return CORRECTION_FACTOR


async def finish_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        val = update.callback_query.data.replace("target_", "")
        context.user_data['target_glucose'] = int(val)
    else:
        try:
            context.user_data['target_glucose'] = int(update.message.text.strip().split()[0])
        except (ValueError, IndexError):
            context.user_data['target_glucose'] = 120

    try:
        upsert_user_profile(
            telegram_user_id=(update.callback_query or update.message).from_user.id,
            age=context.user_data['age'],
            weight=context.user_data['weight'],
            height=context.user_data['height'],
            last_hba1c=context.user_data['last_hba1c'],
            basal_insulin_dose=context.user_data['basal_dose'],
            basal_insulin_time=context.user_data['basal_time'],
            insulin_carb_ratio=context.user_data['icr'],
            correction_factor=context.user_data['correction_factor'],
            target_glucose=context.user_data['target_glucose'],
        )
        summary = (
            "✅ Perfil salvo!\n\n"
            f"Idade: {context.user_data['age']} | Peso: {context.user_data['weight']}kg\n"
            f"Altura: {context.user_data['height']}m | HbA1c: {context.user_data['last_hba1c']}%\n"
            f"Basal: {context.user_data['basal_dose']}U as {context.user_data['basal_time']}\n"
            f"ICR: 1U/{context.user_data['icr']}g | FC: 1U/{context.user_data['correction_factor']}mg/dL\n"
            f"Alvo: {context.user_data['target_glucose']} mg/dL"
        )
        effective = update.callback_query.message if update.callback_query else update.message
        await effective.reply_text(summary, reply_markup=_main_menu_keyboard())
    except Exception as e:
        logging.error(f"Erro onboarding: {e}")
        effective = update.callback_query.message if update.callback_query else update.message
        await effective.reply_text("Falha ao salvar perfil.")

    context.user_data.clear()
    return ConversationHandler.END


# =====================================================================
# FLUXO DE REGISTRO (/registrar)
# =====================================================================

async def start_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        user_id = update.callback_query.from_user.id
        msg_func = update.callback_query.edit_message_text
    else:
        user_id = update.message.from_user.id
        msg_func = update.message.reply_text

    profile = get_user_profile(user_id)
    if not profile or not profile.get('insulin_carb_ratio'):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 Configurar Perfil", callback_data="cmd_perfil")]
        ])
        await msg_func("Configure seu perfil primeiro.", reply_markup=kb)
        return ConversationHandler.END

    context.user_data['profile'] = profile
    context.user_data['food_items'] = []
    context.user_data['total_carbs'] = 0.0
    await msg_func("Qual a sua glicemia atual (mg/dL)?")
    return REG_GLUCOSE


async def receive_glucose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _extract_text(update, context)
    if not text:
        return REG_GLUCOSE
    try:
        glucose = int(text.strip().split()[0])
        context.user_data['glucose'] = glucose

        status = format_glucose_status(glucose)

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🍽 Sim, vou comer", callback_data="food_yes")],
            [InlineKeyboardButton("📸 Enviar foto do prato", callback_data="food_photo")],
            [InlineKeyboardButton("⭐ Usar refeicao salva", callback_data="food_saved")],
            [InlineKeyboardButton("❌ Nao vou comer", callback_data="food_no")],
        ])
        await update.message.reply_text(
            f"Glicemia: {status}\n\nVoce vai comer agora?",
            reply_markup=kb
        )
        return REG_FOOD_CHOICE
    except (ValueError, IndexError):
        await update.message.reply_text("Insira a glicemia em numeros (ex: 120).")
        return REG_GLUCOSE


async def food_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "food_no":
        context.user_data['food_desc'] = "Sem refeicao"
        return await _ask_mood(query)

    if choice == "food_photo":
        await query.edit_message_text(
            "📸 Envie uma foto do seu prato.\n"
            "A IA vai identificar os alimentos e estimar as porcoes."
        )
        return REG_FOOD_SEARCH  # Reutilizamos o estado, mas com photo handler

    if choice == "food_saved":
        user_id = query.from_user.id
        meals = get_saved_meals(user_id)
        if not meals:
            await query.edit_message_text("Nenhuma refeicao salva. Digite o nome do alimento:")
            return REG_FOOD_SEARCH

        buttons = []
        for meal in meals[:8]:
            label = f"⭐ {meal['meal_name']} ({meal['total_carbs']}g carbs)"
            buttons.append([InlineKeyboardButton(label, callback_data=f"meal_{meal['id']}")])
        buttons.append([InlineKeyboardButton("↩️ Voltar", callback_data="food_yes")])
        await query.edit_message_text("Suas refeicoes salvas:", reply_markup=InlineKeyboardMarkup(buttons))
        return REG_MEAL_SELECT

    # food_yes
    await query.edit_message_text(
        "🔍 Digite o nome do alimento (ex: arroz, feijao, frango)\n"
        "📸 Ou envie uma foto do prato"
    )
    return REG_FOOD_SEARCH


async def meal_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "food_yes":
        await query.edit_message_text("Digite o nome do alimento:")
        return REG_FOOD_SEARCH

    meal_id = int(data.replace("meal_", ""))
    user_id = query.from_user.id
    meals = get_saved_meals(user_id)
    meal = next((m for m in meals if m['id'] == meal_id), None)

    if not meal:
        await query.edit_message_text("Refeicao nao encontrada. Digite o alimento:")
        return REG_FOOD_SEARCH

    items = meal['items'] if isinstance(meal['items'], list) else json.loads(meal['items'])
    context.user_data['food_items'] = items
    context.user_data['total_carbs'] = meal['total_carbs']
    context.user_data['food_desc'] = meal['meal_name']

    lines = [f"⭐ Refeicao: {meal['meal_name']}\n"]
    for item in items:
        lines.append(f"  {item['food_name']}: {item['quantity_g']}g = {item['carbs']}g carbs")
    lines.append(f"\n📊 Total: {meal['total_carbs']}g carboidratos")

    await query.edit_message_text("\n".join(lines))
    return await _ask_mood(query)


async def food_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Verificar se e uma foto
    if update.message.photo:
        return await _process_food_photo(update, context)

    text = await _extract_text(update, context)
    if not text:
        return REG_FOOD_SEARCH

    query_text = text.strip()
    results = search_food(query_text, limit=6)

    if not results:
        await update.message.reply_text(
            f"Nenhum resultado para '{query_text}'.\nTente outro nome:"
        )
        return REG_FOOD_SEARCH

    buttons = []
    for item in results:
        label = f"{item['food_name']} ({item['carbs_per_portion']}g/100g)"
        buttons.append([InlineKeyboardButton(label, callback_data=f"food_{item['id']}")])

    await update.message.reply_text(
        f"🔍 Resultados para '{query_text}':",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return REG_FOOD_SELECT


async def _process_food_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa foto de refeicao com visao computacional."""
    await update.message.reply_text("📸 Analisando foto do prato...")

    try:
        from services.vision_service import process_telegram_photo
        photo = update.message.photo[-1]  # maior resolucao
        result = await process_telegram_photo(photo, context)

        if not result.get("success") or not result.get("items"):
            await update.message.reply_text(
                "Nao consegui identificar alimentos na foto.\n"
                "Digite o nome do alimento manualmente:"
            )
            return REG_FOOD_SEARCH

        # Adicionar itens identificados
        for item in result["items"]:
            if item.get("carbs") is not None:
                context.user_data['food_items'].append({
                    "food_name": item["food_name"],
                    "quantity_g": item["quantity_g"],
                    "carbs": item["carbs"],
                })
                context.user_data['total_carbs'] = round(
                    context.user_data['total_carbs'] + item["carbs"], 1
                )

        items = context.user_data['food_items']
        lines = ["📸 Alimentos identificados:\n"]
        for i in items:
            lines.append(f"  {i['food_name']}: {i['quantity_g']}g = {i['carbs']}g carbs")
        lines.append(f"\n📊 Total: {context.user_data['total_carbs']}g carboidratos")

        # Itens nao encontrados na TACO
        unmatched = [i for i in result["items"] if not i.get("matched_taco")]
        if unmatched:
            lines.append("\n⚠️ Nao encontrado na TACO:")
            for u in unmatched:
                lines.append(f"  {u['food_name']} (~{u['quantity_g']}g)")

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirmar", callback_data="more_no")],
            [InlineKeyboardButton("➕ Adicionar mais", callback_data="more_yes")],
            [InlineKeyboardButton("🔄 Refazer manualmente", callback_data="more_redo")],
        ])
        await update.message.reply_text("\n".join(lines), reply_markup=kb)
        return REG_FOOD_MORE

    except Exception as e:
        logging.error(f"Erro visao computacional: {e}")
        await update.message.reply_text(
            "Erro ao analisar foto. Digite o nome do alimento:"
        )
        return REG_FOOD_SEARCH


async def food_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    food_id = int(query.data.replace("food_", ""))
    food = get_food_by_id(food_id)

    if not food:
        await query.edit_message_text("Alimento nao encontrado. Tente novamente:")
        return REG_FOOD_SEARCH

    context.user_data['current_food'] = food
    await query.edit_message_text(
        f"✅ Selecionado: {food['food_name']}\n"
        f"({food['carbs_per_portion']}g carbs por 100g)\n\n"
        f"Quanto voce vai consumir?\n\n"
        f"{format_portion_help()}"
    )
    return REG_FOOD_QTY


async def food_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _extract_text(update, context)
    if not text:
        return REG_FOOD_QTY

    food = context.user_data.get('current_food', {})
    quantity_g = parse_quantity(text.strip())
    carbs = calculate_carbs_from_portion(food.get('carbs_per_portion', 0), quantity_g)

    item = {
        "food_name": food.get('food_name', ''),
        "quantity_g": quantity_g,
        "carbs": carbs,
    }
    context.user_data['food_items'].append(item)
    context.user_data['total_carbs'] = round(context.user_data['total_carbs'] + carbs, 1)

    items = context.user_data['food_items']
    lines = ["🍽 Alimentos adicionados:\n"]
    for i in items:
        lines.append(f"  {i['food_name']}: {i['quantity_g']}g = {i['carbs']}g carbs")
    lines.append(f"\n📊 Total parcial: {context.user_data['total_carbs']}g carboidratos")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Adicionar mais alimento", callback_data="more_yes")],
        [InlineKeyboardButton("✅ Pronto, finalizar refeicao", callback_data="more_no")],
    ])
    await update.message.reply_text("\n".join(lines), reply_markup=kb)
    return REG_FOOD_MORE


async def food_more_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "more_yes":
        await query.edit_message_text(
            "🔍 Digite o nome do proximo alimento\n"
            "📸 Ou envie uma foto"
        )
        return REG_FOOD_SEARCH

    if query.data == "more_redo":
        context.user_data['food_items'] = []
        context.user_data['total_carbs'] = 0.0
        await query.edit_message_text("🔍 Digite o nome do alimento:")
        return REG_FOOD_SEARCH

    # Pronto -> montar descricao
    items = context.user_data['food_items']
    context.user_data['food_desc'] = ", ".join(i['food_name'] for i in items)
    return await _ask_mood(query)


# =====================================================================
# HUMOR
# =====================================================================

async def _ask_mood(query_or_msg) -> int:
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("😊 Bem", callback_data="mood_Bem"),
            InlineKeyboardButton("😐 Normal", callback_data="mood_Normal"),
        ],
        [
            InlineKeyboardButton("😤 Estressado", callback_data="mood_Estressado"),
            InlineKeyboardButton("😰 Ansioso", callback_data="mood_Ansioso"),
        ],
        [
            InlineKeyboardButton("😢 Triste", callback_data="mood_Triste"),
            InlineKeyboardButton("⏭ Pular", callback_data="mood_skip"),
        ],
    ])
    if hasattr(query_or_msg, 'edit_message_text'):
        await query_or_msg.edit_message_text("Como voce esta se sentindo?", reply_markup=kb)
    else:
        await query_or_msg.message.reply_text("Como voce esta se sentindo?", reply_markup=kb)
    return REG_MOOD


async def mood_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    mood = query.data.replace("mood_", "")
    context.user_data['mood'] = None if mood == "skip" else mood

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Nenhum", callback_data="ex_nenhum")],
        [
            InlineKeyboardButton("🚶 Leve (-10%)", callback_data="ex_leve"),
            InlineKeyboardButton("🏃 Moderado (-20%)", callback_data="ex_moderado"),
        ],
        [InlineKeyboardButton("🏋️ Intenso (-30%)", callback_data="ex_intenso")],
    ])
    await query.edit_message_text(
        "Fez ou vai fazer exercicio?\n\n"
        "Exercicio aumenta a sensibilidade a insulina,\n"
        "reduzindo a dose necessaria.",
        reply_markup=kb
    )
    return REG_EXERCISE


# =====================================================================
# EXERCICIO
# =====================================================================

async def exercise_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    intensity = query.data.replace("ex_", "")
    context.user_data['exercise_intensity'] = intensity
    context.user_data['exercise_done'] = intensity != "nenhum"

    # Calcular dose
    profile = context.user_data['profile']
    glucose = context.user_data.get('glucose', 0)
    total_carbs = context.user_data.get('total_carbs', 0.0)

    calc = calculate_total_dose(
        carbs_ingested=total_carbs,
        current_glucose=glucose,
        insulin_carb_ratio=profile.get('insulin_carb_ratio', 10),
        correction_factor=profile.get('correction_factor', 50),
        target_glucose=profile.get('target_glucose', 120),
        exercise_intensity=intensity,
    )
    context.user_data['calc'] = calc

    # Formatar resultado com mensagem empatica
    lines = ["💉 CALCULO DE DOSE\n"]

    if calc["carbs_ingested"] > 0:
        lines.append(
            f"🍽 Bolus: {calc['carbs_ingested']}g / {calc['insulin_carb_ratio']} (ICR) "
            f"= {calc['bolus_alimentar']}U"
        )

    if glucose > calc["target_glucose"]:
        lines.append(
            f"📐 Correcao: ({glucose} - {calc['target_glucose']}) / {calc['correction_factor']} "
            f"= {calc['dose_correcao']}U"
        )

    if calc["exercise_reduction"] > 0:
        lines.append(
            f"🏃 Exercicio {intensity}: -{calc['exercise_reduction']}U "
            f"({int((1 - calc['exercise_factor']) * 100)}% reducao)"
        )

    if glucose < 70:
        lines.append("\n⚠️ Glicemia baixa - cuidado ao aplicar insulina!")
    elif glucose > 250:
        lines.append("\n⚠️ Hiperglicemia severa - considere verificar cetonas.")

    lines.append(f"\n💉 DOSE TOTAL SUGERIDA: {calc['dose_total']}U")
    lines.append("\nQuantas unidades voce aplicou?")

    await query.edit_message_text("\n".join(lines))
    return REG_INSULIN


# =====================================================================
# INSULINA APLICADA
# =====================================================================

async def receive_insulin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _extract_text(update, context)
    if not text:
        return REG_INSULIN
    try:
        applied = float(text.replace(',', '.').strip().split()[0])
        calc = context.user_data.get('calc', {})
        suggested = calc.get('dose_total', 0)
        glucose = context.user_data.get('glucose', 0)
        total_carbs = context.user_data.get('total_carbs', 0.0)

        insert_glycemic_log(
            telegram_user_id=update.message.from_user.id,
            glucose_level=glucose,
            carbs_ingested=total_carbs,
            bolus_insulin=applied,
            exercise_done=context.user_data.get('exercise_done', False),
            exercise_intensity=context.user_data.get('exercise_intensity'),
            mood=context.user_data.get('mood'),
            refeicao=context.user_data.get('food_desc', 'Sem refeicao'),
        )

        diff_text = ""
        if suggested > 0 and applied != suggested:
            diff = round(applied - suggested, 2)
            if diff > 0:
                diff_text = f"\n({diff}U a mais que o sugerido)"
            else:
                diff_text = f"\n({abs(diff)}U a menos que o sugerido)"

        # Perguntar se quer salvar a refeicao
        items = context.user_data.get('food_items', [])
        if items:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⭐ Salvar refeicao como favorita", callback_data="save_meal_yes")],
                [InlineKeyboardButton("✅ Finalizar", callback_data="save_meal_no")],
            ])
            await update.message.reply_text(
                f"✅ Registro salvo!{diff_text}\n\n"
                f"Glic: {glucose} mg/dL | Carbs: {total_carbs}g\n"
                f"Aplicou: {applied}U | Sugerido: {suggested}U\n\n"
                "Deseja salvar esta refeicao como favorita?",
                reply_markup=kb
            )
            return REG_SAVE_MEAL_CHOICE
        else:
            await update.message.reply_text(
                f"✅ Registro salvo!{diff_text}\n\n"
                f"Glic: {glucose} mg/dL | Aplicou: {applied}U | Sugerido: {suggested}U",
                reply_markup=_main_menu_keyboard()
            )
            context.user_data.clear()
            return ConversationHandler.END

    except (ValueError, IndexError):
        await update.message.reply_text("Insira um numero (ex: 5 ou 5.5).")
        return REG_INSULIN


# =====================================================================
# SALVAR REFEICAO
# =====================================================================

async def save_meal_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "save_meal_no":
        await query.edit_message_text("✅ Registro finalizado!", reply_markup=_main_menu_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    await query.edit_message_text("Digite um nome para esta refeicao (ex: Almoco padrao):")
    return REG_SAVE_MEAL_NAME


async def save_meal_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    items = context.user_data.get('food_items', [])
    total_carbs = context.user_data.get('total_carbs', 0.0)

    try:
        save_meal(
            telegram_user_id=update.message.from_user.id,
            meal_name=name,
            items=items,
            total_carbs=total_carbs,
        )
        await update.message.reply_text(
            f"⭐ Refeicao '{name}' salva com sucesso!",
            reply_markup=_main_menu_keyboard()
        )
    except Exception as e:
        logging.error(f"Erro ao salvar refeicao: {e}")
        await update.message.reply_text("Erro ao salvar.", reply_markup=_main_menu_keyboard())

    context.user_data.clear()
    return ConversationHandler.END


# =====================================================================
# FLUXO DO SENSOR CGM
# =====================================================================

async def start_sensor_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de conexao do sensor FreeStyle Libre."""
    if update.callback_query:
        await update.callback_query.answer()
        user_id = update.callback_query.from_user.id
        msg_func = update.callback_query.edit_message_text
    else:
        user_id = update.message.from_user.id
        msg_func = update.message.reply_text

    # Verificar se ja tem integracao
    from repositories.sensor_repository import get_sensor_integration
    existing = get_sensor_integration(user_id)
    if existing:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Reconfigurar", callback_data="sensor_reconfig")],
            [InlineKeyboardButton("❌ Desconectar sensor", callback_data="sensor_disconnect")],
            [InlineKeyboardButton("↩️ Voltar", callback_data="cmd_menu")],
        ])
        status = "🟢 Conectado" if existing.get("status") == "ACTIVE" else "🔴 Inativo"
        last_sync = existing.get("last_sync_timestamp", "Nunca")
        if isinstance(last_sync, str) and len(last_sync) > 16:
            last_sync = last_sync[:16].replace("T", " ")
        await msg_func(
            f"🩸 Sensor CGM\n\n"
            f"Status: {status}\n"
            f"Email: {existing['llu_email']}\n"
            f"Regiao: {existing.get('llu_region_code', 'BR')}\n"
            f"Ultima sync: {last_sync}",
            reply_markup=kb
        )
        return ConversationHandler.END

    await msg_func(
        "🩸 Conectar FreeStyle Libre 2 Plus\n\n"
        "Para monitoramento automatico, precisamos das\n"
        "credenciais do LibreLinkUp (app de compartilhamento).\n\n"
        "1. Instale o LibreLink no celular\n"
        "2. Ative o compartilhamento no LibreLinkUp\n"
        "3. Crie uma conta de seguidor\n\n"
        "Digite o EMAIL do LibreLinkUp:"
    )
    return SENSOR_EMAIL


async def sensor_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text.strip()
    if "@" not in email:
        await update.message.reply_text("Email invalido. Tente novamente:")
        return SENSOR_EMAIL
    context.user_data['llu_email'] = email
    await update.message.reply_text("🔒 Digite a SENHA do LibreLinkUp:")
    return SENSOR_PASSWORD


async def sensor_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['llu_password'] = update.message.text.strip()
    # Tentar deletar a mensagem com a senha por seguranca
    try:
        await update.message.delete()
    except Exception:
        pass

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇧🇷 Brasil", callback_data="region_BR"),
            InlineKeyboardButton("🇺🇸 EUA", callback_data="region_US"),
        ],
        [
            InlineKeyboardButton("🇪🇺 Europa", callback_data="region_EU"),
            InlineKeyboardButton("🇦🇺 Oceania", callback_data="region_AU"),
        ],
    ])
    await update.message.reply_text(
        "🔒 Senha recebida.\n\nSelecione sua regiao:", reply_markup=kb
    )
    return SENSOR_REGION


async def sensor_region_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    region = query.data.replace("region_", "")
    context.user_data['llu_region'] = region

    await query.edit_message_text("🔄 Validando credenciais...")

    from services.libre_service import validate_credentials
    result = validate_credentials(
        email=context.user_data['llu_email'],
        password=context.user_data['llu_password'],
        region=region,
    )

    if not result.get("valid"):
        error = result.get("error", "Erro desconhecido")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Tentar novamente", callback_data="cmd_sensor")],
            [InlineKeyboardButton("↩️ Voltar", callback_data="cmd_menu")],
        ])
        await query.edit_message_text(
            f"❌ Falha na validacao: {error}", reply_markup=kb
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Salvar integracao
    from repositories.sensor_repository import upsert_sensor_integration
    upsert_sensor_integration(
        telegram_user_id=query.from_user.id,
        llu_email=context.user_data['llu_email'],
        llu_password=context.user_data['llu_password'],
        llu_region_code=region,
    )

    latest = result.get("latest_glucose")
    glucose_text = ""
    if latest:
        glucose_text = f"\n\n📊 Leitura atual: {latest['glucose_value']} mg/dL"

    await query.edit_message_text(
        f"✅ Sensor conectado com sucesso!{glucose_text}\n\n"
        "O bot agora ira sincronizar automaticamente\n"
        "e enviar alertas proativos quando necessario.",
        reply_markup=_main_menu_keyboard()
    )

    context.user_data.clear()
    return ConversationHandler.END


async def sensor_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Callback para acoes do sensor (reconfigurar/desconectar)."""
    query = update.callback_query
    await query.answer()

    if query.data == "sensor_disconnect":
        from repositories.sensor_repository import deactivate_sensor_integration
        deactivate_sensor_integration(query.from_user.id)
        await query.edit_message_text(
            "🩸 Sensor desconectado.",
            reply_markup=_main_menu_keyboard()
        )
        return ConversationHandler.END

    if query.data == "sensor_reconfig":
        await query.edit_message_text(
            "Digite o EMAIL do LibreLinkUp:"
        )
        return SENSOR_EMAIL

    return ConversationHandler.END


# =====================================================================
# FLUXO DO DIGITAL TWIN (Simulacao)
# =====================================================================

async def start_simulation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia simulacao de impacto de refeicao na glicemia."""
    if update.callback_query:
        await update.callback_query.answer()
        user_id = update.callback_query.from_user.id
        msg_func = update.callback_query.edit_message_text
    else:
        user_id = update.message.from_user.id
        msg_func = update.message.reply_text

    profile = get_user_profile(user_id)
    if not profile or not profile.get('insulin_carb_ratio'):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 Configurar Perfil", callback_data="cmd_perfil")]
        ])
        await msg_func("Configure seu perfil primeiro.", reply_markup=kb)
        return ConversationHandler.END

    context.user_data['sim_profile'] = profile
    context.user_data['sim_items'] = []
    context.user_data['sim_carbs'] = 0.0

    # Obter glicemia mais recente
    recent = get_recent_logs(user_id, limit=1)
    if recent:
        context.user_data['sim_glucose'] = recent[0].get('glucose_level', 120)
    else:
        context.user_data['sim_glucose'] = 120

    await msg_func(
        "🔮 Simulacao de Gemeo Digital\n\n"
        "Simule o impacto de uma refeicao ANTES de comer.\n"
        "Vou projetar como sua glicemia vai se comportar.\n\n"
        "🔍 Digite o alimento que pretende comer:"
    )
    return TWIN_FOOD_SEARCH


async def twin_food_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _extract_text(update, context)
    if not text:
        return TWIN_FOOD_SEARCH

    results = search_food(text.strip(), limit=6)
    if not results:
        await update.message.reply_text("Nenhum resultado. Tente outro nome:")
        return TWIN_FOOD_SEARCH

    buttons = []
    for item in results:
        label = f"{item['food_name']} ({item['carbs_per_portion']}g/100g)"
        buttons.append([InlineKeyboardButton(label, callback_data=f"twfood_{item['id']}")])

    await update.message.reply_text(
        "Selecione o alimento:", reply_markup=InlineKeyboardMarkup(buttons)
    )
    return TWIN_FOOD_SELECT


async def twin_food_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    food_id = int(query.data.replace("twfood_", ""))
    food = get_food_by_id(food_id)
    if not food:
        await query.edit_message_text("Alimento nao encontrado. Tente novamente:")
        return TWIN_FOOD_SEARCH

    context.user_data['sim_current_food'] = food
    await query.edit_message_text(
        f"✅ {food['food_name']} ({food['carbs_per_portion']}g carbs/100g)\n\n"
        f"Quanto pretende consumir?\n{format_portion_help()}"
    )
    return TWIN_FOOD_QTY


async def twin_food_qty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _extract_text(update, context)
    if not text:
        return TWIN_FOOD_QTY

    food = context.user_data.get('sim_current_food', {})
    quantity_g = parse_quantity(text.strip())
    carbs = calculate_carbs_from_portion(food.get('carbs_per_portion', 0), quantity_g)

    context.user_data['sim_items'].append({
        "food_name": food.get('food_name', ''),
        "quantity_g": quantity_g,
        "carbs": carbs,
    })
    context.user_data['sim_carbs'] = round(context.user_data['sim_carbs'] + carbs, 1)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Adicionar mais", callback_data="tw_more_yes")],
        [InlineKeyboardButton("🔮 Simular agora", callback_data="tw_more_no")],
    ])

    items = context.user_data['sim_items']
    lines = ["Alimentos para simulacao:\n"]
    for i in items:
        lines.append(f"  {i['food_name']}: {i['quantity_g']}g = {i['carbs']}g carbs")
    lines.append(f"\nTotal: {context.user_data['sim_carbs']}g carbs")

    await update.message.reply_text("\n".join(lines), reply_markup=kb)
    return TWIN_MORE


async def twin_more_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "tw_more_yes":
        await query.edit_message_text("🔍 Digite o proximo alimento:")
        return TWIN_FOOD_SEARCH

    # Executar simulacao
    await query.edit_message_text("🔮 Calculando simulacao...")

    profile = context.user_data['sim_profile']
    glucose = context.user_data.get('sim_glucose', 120)
    carbs = context.user_data.get('sim_carbs', 0)
    icr = profile.get('insulin_carb_ratio', 10)
    fc = profile.get('correction_factor', 50)
    target = profile.get('target_glucose', 120)

    # Calcular dose sugerida
    calc = calculate_total_dose(
        carbs_ingested=carbs,
        current_glucose=glucose,
        insulin_carb_ratio=icr,
        correction_factor=fc,
        target_glucose=target,
    )
    dose = calc['dose_total']

    # Simular curva
    from ml_engine.prediction_service import simulate_meal_impact
    curve = simulate_meal_impact(
        current_glucose=glucose,
        carbs=carbs,
        icr=icr,
        correction_factor=fc,
        target_glucose=target,
        insulin_dose=dose,
    )

    # Formatar resultado
    peak = max(curve, key=lambda p: p['predicted_glucose'])
    valley = min(curve, key=lambda p: p['predicted_glucose'])

    lines = [
        "🔮 SIMULACAO - Gemeo Digital\n",
        f"📊 Glicemia atual: {int(glucose)} mg/dL",
        f"🍽 Carboidratos: {carbs}g",
        f"💉 Dose sugerida: {dose}U\n",
        "📈 Projecao de 4 horas:\n",
    ]

    # Curva simplificada a cada hora
    for point in curve:
        if point['minutes'] % 60 == 0:
            t = point['minutes'] // 60
            g = int(point['predicted_glucose'])
            bar_len = max(1, min(20, int((g - 40) / 20)))
            bar = "█" * bar_len
            emoji = "🟢" if 70 <= g <= 180 else "🟡" if g <= 250 else "🔴"
            lines.append(f"  {t}h: {emoji} {g} mg/dL {bar}")

    lines.append(f"\n📈 Pico previsto: {int(peak['predicted_glucose'])} mg/dL (em {peak['minutes']}min)")
    lines.append(f"📉 Minimo previsto: {int(valley['predicted_glucose'])} mg/dL (em {valley['minutes']}min)")

    if peak['predicted_glucose'] > 180:
        lines.append(
            "\n💡 O pico ultrapassa 180 mg/dL. Uma caminhada de 15min "
            "apos a refeicao pode reduzir o pico em ate 30%."
        )

    await query.edit_message_text("\n".join(lines), reply_markup=_main_menu_keyboard())
    context.user_data.clear()
    return ConversationHandler.END


# =====================================================================
# CANCELAR
# =====================================================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Operacao cancelada.")
    else:
        await update.message.reply_text("Operacao cancelada.", reply_markup=_main_menu_keyboard())
    context.user_data.clear()
    return ConversationHandler.END


# =====================================================================
# CONVERSATION HANDLERS
# =====================================================================

_voice_text_filter = (TEXT_FILTER | VOICE_FILTER)

onboarding_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler('perfil', start_onboarding),
        CallbackQueryHandler(start_onboarding, pattern='^cmd_perfil$'),
    ],
    states={
        AGE: [MessageHandler(_voice_text_filter, ask_weight)],
        WEIGHT: [MessageHandler(_voice_text_filter, ask_height)],
        HEIGHT: [MessageHandler(_voice_text_filter, ask_hba1c)],
        HBA1C: [MessageHandler(_voice_text_filter, ask_basal_dose)],
        BASAL_DOSE: [MessageHandler(_voice_text_filter, ask_basal_time)],
        BASAL_TIME: [MessageHandler(_voice_text_filter, ask_icr)],
        ICR: [MessageHandler(_voice_text_filter, ask_correction_factor)],
        CORRECTION_FACTOR: [MessageHandler(_voice_text_filter, ask_target_glucose)],
        TARGET_GLUCOSE: [
            CallbackQueryHandler(finish_onboarding, pattern='^target_'),
            MessageHandler(_voice_text_filter, finish_onboarding),
        ],
    },
    fallbacks=[CommandHandler('cancelar', cancel)]
)

log_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler('registrar', start_log),
        CallbackQueryHandler(start_log, pattern='^cmd_registrar$'),
    ],
    states={
        REG_GLUCOSE: [MessageHandler(_voice_text_filter, receive_glucose)],
        REG_FOOD_CHOICE: [CallbackQueryHandler(food_choice_callback)],
        REG_FOOD_SEARCH: [
            MessageHandler(PHOTO_FILTER, _process_food_photo),
            MessageHandler(_voice_text_filter, food_search),
        ],
        REG_FOOD_SELECT: [CallbackQueryHandler(food_select_callback)],
        REG_FOOD_QTY: [MessageHandler(_voice_text_filter, food_quantity)],
        REG_FOOD_MORE: [CallbackQueryHandler(food_more_callback)],
        REG_MOOD: [CallbackQueryHandler(mood_callback)],
        REG_EXERCISE: [CallbackQueryHandler(exercise_callback)],
        REG_INSULIN: [MessageHandler(_voice_text_filter, receive_insulin)],
        REG_SAVE_MEAL_CHOICE: [CallbackQueryHandler(save_meal_choice_callback)],
        REG_SAVE_MEAL_NAME: [MessageHandler(TEXT_FILTER, save_meal_name)],
        REG_MEAL_SELECT: [CallbackQueryHandler(meal_select_callback)],
    },
    fallbacks=[CommandHandler('cancelar', cancel)]
)

sensor_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler('sensor', start_sensor_setup),
        CallbackQueryHandler(start_sensor_setup, pattern='^cmd_sensor$'),
    ],
    states={
        SENSOR_EMAIL: [MessageHandler(TEXT_FILTER, sensor_email)],
        SENSOR_PASSWORD: [MessageHandler(TEXT_FILTER, sensor_password)],
        SENSOR_REGION: [CallbackQueryHandler(sensor_region_callback, pattern='^region_')],
    },
    fallbacks=[
        CommandHandler('cancelar', cancel),
        CallbackQueryHandler(sensor_action_callback, pattern='^sensor_'),
    ]
)

simulation_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler('simular', start_simulation),
        CallbackQueryHandler(start_simulation, pattern='^cmd_simular$'),
    ],
    states={
        TWIN_FOOD_SEARCH: [MessageHandler(_voice_text_filter, twin_food_search)],
        TWIN_FOOD_SELECT: [CallbackQueryHandler(twin_food_select, pattern='^twfood_')],
        TWIN_FOOD_QTY: [MessageHandler(_voice_text_filter, twin_food_qty)],
        TWIN_MORE: [CallbackQueryHandler(twin_more_callback, pattern='^tw_more_')],
    },
    fallbacks=[CommandHandler('cancelar', cancel)]
)
