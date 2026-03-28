# handlers/telegram_handlers.py
import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters
)
from services.nlp_service import extract_health_data
from services.calculator_service import calculate_total_dose
from services.chart_service import generate_glucose_chart
from services.voice_service import transcribe_voice
from repositories.logs_repository import insert_glycemic_log, get_recent_logs, get_logs_for_period
from repositories.user_repository import upsert_user_profile, get_user_profile
from repositories.food_repository import search_food

# --- ESTADOS DO ONBOARDING ---
AGE, WEIGHT, HEIGHT, HBA1C, BASAL_DOSE, BASAL_TIME, ICR, CORRECTION_FACTOR, TARGET_GLUCOSE = range(9)

# --- ESTADOS DO REGISTRO DIARIO ---
GLUCOSE_STATE, FOOD_STATE, INSULIN_STATE = range(9, 12)


# =====================================================================
# UTILIDADES
# =====================================================================

async def _get_text_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Extrai texto de uma mensagem de texto ou de voz."""
    if update.message.voice:
        processing = await update.message.reply_text("Transcrevendo audio...")
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        audio_bytes = await voice_file.download_as_bytearray()
        text = await transcribe_voice(audio_bytes)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=processing.message_id,
            text=f"Entendi: \"{text}\""
        )
        return text
    return update.message.text


def _format_dose_calculation(calc: dict, glucose: int) -> str:
    """Formata o resultado do calculo de dose para exibicao."""
    lines = []
    lines.append("--- Calculo de Dose ---\n")

    if calc["carbs_ingested"] > 0:
        lines.append(
            f"Bolus alimentar: {calc['carbs_ingested']}g / {calc['insulin_carb_ratio']} (ICR) "
            f"= {calc['bolus_alimentar']} U"
        )

    if glucose > calc["target_glucose"]:
        diff = glucose - calc["target_glucose"]
        lines.append(
            f"Correcao: ({glucose} - {calc['target_glucose']}) / {calc['correction_factor']} (FC) "
            f"= {calc['dose_correcao']} U"
        )
    elif glucose < 70:
        lines.append(f"Atencao: Glicemia {glucose} mg/dL esta BAIXA. Considere ingerir carboidratos.")

    lines.append(f"\nDOSE TOTAL SUGERIDA: {calc['dose_total']} U")
    lines.append(f"\nQuantas unidades voce aplicou de fato? (texto ou audio)")
    return "\n".join(lines)


# =====================================================================
# COMANDO /start
# =====================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome = (
        "Ola! Eu sou o GlycemiBot, seu assistente de monitoramento glicemico.\n\n"
        "Voce pode interagir por TEXTO ou AUDIO em qualquer etapa.\n\n"
        "Comandos disponiveis:\n"
        "/perfil - Configurar seu perfil clinico\n"
        "/registrar - Registrar glicemia e calcular insulina\n"
        "/historico - Ver seus ultimos 10 registros\n"
        "/grafico - Grafico glicemico dos ultimos 7 dias\n"
        "/buscar - Buscar alimento na tabela TACO\n"
        "/ajuda - Ver ajuda detalhada\n"
        "/cancelar - Cancelar operacao em andamento"
    )
    await update.message.reply_text(welcome)


# =====================================================================
# COMANDO /ajuda
# =====================================================================

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "GlycemiBot - Ajuda Detalhada\n\n"
        "CONFIGURACAO:\n"
        "/perfil - Cadastra seus dados clinicos:\n"
        "  - Idade, peso, altura, HbA1c\n"
        "  - Dose e horario de insulina basal\n"
        "  - Razao Insulina/Carboidrato (ICR)\n"
        "  - Fator de Correcao (FC)\n"
        "  - Glicemia alvo\n\n"
        "REGISTRO DIARIO:\n"
        "/registrar - Novo registro (aceita texto ou audio):\n"
        "  1. Informe sua glicemia atual\n"
        "  2. Descreva sua refeicao (ou 'nada')\n"
        "  3. O bot calcula a dose:\n"
        "     Bolus = carboidratos / ICR\n"
        "     Correcao = (glicemia - alvo) / FC\n"
        "     Dose total = Bolus + Correcao\n"
        "  4. Informe a insulina que aplicou\n\n"
        "CONSULTAS:\n"
        "/historico - Ultimos 10 registros\n"
        "/grafico - Grafico de 7 dias\n"
        "/buscar <alimento> - Carboidratos na tabela TACO\n\n"
        "/cancelar - Cancela qualquer operacao"
    )
    await update.message.reply_text(help_text)


# =====================================================================
# COMANDO /historico
# =====================================================================

async def historico(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    logs = get_recent_logs(user_id, limit=10)

    if not logs:
        await update.message.reply_text("Nenhum registro encontrado. Use /registrar para comecar.")
        return

    lines = ["Ultimos registros:\n"]
    for log in logs:
        ts = log.get("timestamp", "")[:16].replace("T", " ")
        glucose = log.get("glucose_level", "-")
        carbs = log.get("carbs_ingested", "-")
        bolus = log.get("bolus_insulin", "-")
        refeicao = log.get("refeicao", "-")
        lines.append(
            f"  {ts}\n"
            f"  Glicemia: {glucose} mg/dL | Carbs: {carbs}g | Insulina: {bolus}U\n"
            f"  Refeicao: {refeicao}\n"
        )

    await update.message.reply_text("\n".join(lines))


# =====================================================================
# COMANDO /grafico
# =====================================================================

async def grafico(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    logs = get_logs_for_period(user_id, days=7)

    if not logs:
        await update.message.reply_text("Sem registros nos ultimos 7 dias para gerar o grafico.")
        return

    try:
        chart_buf = generate_glucose_chart(logs)
        await update.message.reply_photo(
            photo=chart_buf,
            caption="Historico glicemico dos ultimos 7 dias."
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        logging.error(f"Erro ao gerar grafico: {e}")
        await update.message.reply_text("Erro ao gerar o grafico. Tente novamente.")


# =====================================================================
# COMANDO /buscar
# =====================================================================

async def buscar_alimento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args) if context.args else ""

    if not query:
        await update.message.reply_text("Use: /buscar <nome do alimento>\nExemplo: /buscar arroz")
        return

    results = search_food(query, limit=5)

    if not results:
        await update.message.reply_text(f"Nenhum alimento encontrado para '{query}'.")
        return

    lines = [f"Resultados para '{query}':\n"]
    for item in results:
        name = item.get("food_name", "-")
        carbs = item.get("carbs_per_portion", 0)
        portion = item.get("portion_size", 100)
        unit = item.get("unit", "g")
        lines.append(f"  {name}\n  Carboidratos: {carbs}g por {portion}{unit}\n")

    await update.message.reply_text("\n".join(lines))


# =====================================================================
# FLUXO DE ONBOARDING (/perfil)
# =====================================================================

async def start_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Vamos configurar seu perfil clinico.\n"
        "Voce pode responder por texto ou audio em todas as etapas.\n\n"
        "Qual a sua idade?"
    )
    return AGE


async def ask_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = await _get_text_from_message(update, context)
        context.user_data['age'] = int(text.strip().split()[0])
        await update.message.reply_text("Qual o seu peso atual (em kg)?")
        return WEIGHT
    except (ValueError, IndexError):
        await update.message.reply_text("Por favor, insira um numero inteiro valido para a idade.")
        return AGE


async def ask_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = await _get_text_from_message(update, context)
        context.user_data['weight'] = float(text.strip().replace(',', '.').split()[0])
        await update.message.reply_text("Qual a sua altura (em metros, ex: 1.75)?")
        return HEIGHT
    except (ValueError, IndexError):
        await update.message.reply_text("Formato invalido. Insira o peso em numeros.")
        return WEIGHT


async def ask_hba1c(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = await _get_text_from_message(update, context)
        context.user_data['height'] = float(text.strip().replace(',', '.').split()[0])
        await update.message.reply_text("Qual o valor da sua ultima hemoglobina glicada (HbA1c)?")
        return HBA1C
    except (ValueError, IndexError):
        await update.message.reply_text("Formato invalido. Insira a altura em metros.")
        return HEIGHT


async def ask_basal_dose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = await _get_text_from_message(update, context)
        context.user_data['last_hba1c'] = float(text.strip().replace(',', '.').split()[0])
        await update.message.reply_text("Quantas unidades de insulina BASAL voce aplica diariamente?")
        return BASAL_DOSE
    except (ValueError, IndexError):
        await update.message.reply_text("Formato invalido. Insira o valor numerico da HbA1c.")
        return HBA1C


async def ask_basal_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = await _get_text_from_message(update, context)
        context.user_data['basal_dose'] = float(text.strip().replace(',', '.').split()[0])
        await update.message.reply_text("Em qual horario voce aplica a insulina basal (ex: 22:00)?")
        return BASAL_TIME
    except (ValueError, IndexError):
        await update.message.reply_text("Formato invalido. Insira o numero de unidades.")
        return BASAL_DOSE


async def ask_icr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _get_text_from_message(update, context)
    context.user_data['basal_time'] = text.strip()
    await update.message.reply_text(
        "Qual a sua RAZAO INSULINA/CARBOIDRATO (ICR)?\n\n"
        "Isso significa: quantos gramas de carboidrato 1 unidade de insulina rapida cobre.\n"
        "Exemplo: se voce aplica 1U para cada 10g de carbo, digite 10."
    )
    return ICR


async def ask_correction_factor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = await _get_text_from_message(update, context)
        context.user_data['icr'] = float(text.strip().replace(',', '.').split()[0])
        await update.message.reply_text(
            "Qual o seu FATOR DE CORRECAO (FC)?\n\n"
            "Isso significa: quantos mg/dL 1 unidade de insulina rapida reduz a sua glicemia.\n"
            "Exemplo: se 1U abaixa 50 mg/dL, digite 50."
        )
        return CORRECTION_FACTOR
    except (ValueError, IndexError):
        await update.message.reply_text("Formato invalido. Insira um numero (ex: 10).")
        return ICR


async def ask_target_glucose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = await _get_text_from_message(update, context)
        context.user_data['correction_factor'] = float(text.strip().replace(',', '.').split()[0])
        await update.message.reply_text(
            "Qual a sua GLICEMIA ALVO (mg/dL)?\n\n"
            "O padrao clinico e entre 100-120 mg/dL.\n"
            "Se nao souber, digite 120."
        )
        return TARGET_GLUCOSE
    except (ValueError, IndexError):
        await update.message.reply_text("Formato invalido. Insira um numero (ex: 50).")
        return CORRECTION_FACTOR


async def finish_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = await _get_text_from_message(update, context)
        context.user_data['target_glucose'] = int(text.strip().split()[0])
    except (ValueError, IndexError):
        context.user_data['target_glucose'] = 120

    try:
        upsert_user_profile(
            telegram_user_id=update.message.from_user.id,
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
            "Perfil salvo com sucesso!\n\n"
            f"Idade: {context.user_data['age']} anos\n"
            f"Peso: {context.user_data['weight']} kg\n"
            f"Altura: {context.user_data['height']} m\n"
            f"HbA1c: {context.user_data['last_hba1c']}%\n"
            f"Basal: {context.user_data['basal_dose']}U as {context.user_data['basal_time']}\n"
            f"ICR: 1U para cada {context.user_data['icr']}g de carbo\n"
            f"Fator de Correcao: 1U reduz {context.user_data['correction_factor']} mg/dL\n"
            f"Glicemia alvo: {context.user_data['target_glucose']} mg/dL\n\n"
            "Use /registrar para comecar a registrar sua glicemia."
        )
        await update.message.reply_text(summary)
    except Exception as e:
        await update.message.reply_text("Falha ao salvar o perfil no banco de dados.")
        logging.error(f"Erro no onboarding: {e}")

    context.user_data.clear()
    return ConversationHandler.END


# =====================================================================
# FLUXO DE REGISTRO DIARIO (/registrar)
# =====================================================================

async def start_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    profile = get_user_profile(user_id)

    if not profile or not profile.get('insulin_carb_ratio'):
        await update.message.reply_text(
            "Voce ainda nao configurou seu perfil clinico.\n"
            "Use /perfil primeiro para cadastrar seus dados (ICR, fator de correcao, etc)."
        )
        return ConversationHandler.END

    context.user_data['profile'] = profile
    await update.message.reply_text(
        "Iniciando registro. Qual a sua glicemia atual (mg/dL)?\n"
        "(Pode enviar por texto ou audio)"
    )
    return GLUCOSE_STATE


async def receive_glucose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = await _get_text_from_message(update, context)
        # Extrai o primeiro numero do texto (suporte a voz tipo "cento e vinte" -> dificil, mas "120" funciona)
        numbers = [s for s in text.strip().replace(',', '.').split() if s.replace('.', '').isdigit()]
        if not numbers:
            raise ValueError("Nenhum numero encontrado")
        context.user_data['glucose'] = int(float(numbers[0]))

        glucose = context.user_data['glucose']
        warning = ""
        if glucose < 70:
            warning = "\n⚠ HIPOGLICEMIA DETECTADA. Considere ingerir 15g de carboidrato rapido.\n"
        elif glucose > 250:
            warning = "\n⚠ HIPERGLICEMIA SEVERA. Atencao redobrada.\n"

        await update.message.reply_text(
            f"Glicemia registrada: {glucose} mg/dL.{warning}\n"
            "O que voce vai comer agora?\n"
            "Descreva a refeicao ou diga 'nada'. (texto ou audio)"
        )
        return FOOD_STATE
    except (ValueError, IndexError):
        await update.message.reply_text("Nao entendi. Insira a glicemia em numeros (ex: 120).")
        return GLUCOSE_STATE


async def receive_food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = await _get_text_from_message(update, context)
    food_text = text.lower().strip()

    processing_msg = await update.message.reply_text("Processando informacoes nutricionais...")

    profile = context.user_data['profile']
    glucose = context.user_data['glucose']
    icr = profile.get('insulin_carb_ratio', 10)
    cf = profile.get('correction_factor', 50)
    target = profile.get('target_glucose', 120)

    if food_text in ('nada', 'nao', 'nao vou comer', 'nenhuma', 'nao comi'):
        context.user_data['carbs'] = 0.0
        context.user_data['food_desc'] = "Nenhuma refeicao"
    else:
        try:
            extracted_data = extract_health_data(food_text)
            carbs = extracted_data.get('carbs_ingested', 0.0) or 0.0
            context.user_data['carbs'] = carbs
            context.user_data['food_desc'] = food_text
        except Exception as e:
            logging.error(f"Erro NLP: {e}")
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id,
                text="Erro ao processar a refeicao. Tente novamente."
            )
            return FOOD_STATE

    calc = calculate_total_dose(
        carbs_ingested=context.user_data['carbs'],
        current_glucose=glucose,
        insulin_carb_ratio=icr,
        correction_factor=cf,
        target_glucose=target,
    )
    context.user_data['calc'] = calc

    response_text = _format_dose_calculation(calc, glucose)

    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=processing_msg.message_id,
        text=response_text
    )
    return INSULIN_STATE


async def receive_insulin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = await _get_text_from_message(update, context)
        numbers = [s for s in text.strip().replace(',', '.').split() if s.replace('.', '').isdigit()]
        if not numbers:
            raise ValueError("Nenhum numero encontrado")
        applied_insulin = float(numbers[0])

        calc = context.user_data.get('calc', {})
        suggested = calc.get('dose_total', 0)

        insert_glycemic_log(
            telegram_user_id=update.message.from_user.id,
            glucose_level=context.user_data.get('glucose'),
            carbs_ingested=context.user_data.get('carbs'),
            bolus_insulin=applied_insulin,
            refeicao=context.user_data.get('food_desc', 'Nao especificada')
        )

        diff_text = ""
        if suggested > 0 and applied_insulin != suggested:
            diff = round(applied_insulin - suggested, 2)
            if diff > 0:
                diff_text = f"\n(Voce aplicou {diff}U a mais que o sugerido)"
            elif diff < 0:
                diff_text = f"\n(Voce aplicou {abs(diff)}U a menos que o sugerido)"

        await update.message.reply_text(
            f"Registro salvo com sucesso!{diff_text}\n\n"
            f"Glicemia: {context.user_data.get('glucose')} mg/dL\n"
            f"Carboidratos: {context.user_data.get('carbs')}g\n"
            f"Insulina aplicada: {applied_insulin}U\n"
            f"Dose sugerida: {suggested}U"
        )
        context.user_data.clear()
        return ConversationHandler.END

    except (ValueError, IndexError):
        await update.message.reply_text("Formato invalido. Insira um numero para a insulina aplicada.")
        return INSULIN_STATE


# =====================================================================
# CANCELAR
# =====================================================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operacao cancelada.")
    context.user_data.clear()
    return ConversationHandler.END


# =====================================================================
# CONVERSATION HANDLERS
# =====================================================================

# Filtro que aceita texto OU audio de voz
text_or_voice = (filters.TEXT & ~filters.COMMAND) | filters.VOICE

onboarding_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('perfil', start_onboarding)],
    states={
        AGE: [MessageHandler(text_or_voice, ask_weight)],
        WEIGHT: [MessageHandler(text_or_voice, ask_height)],
        HEIGHT: [MessageHandler(text_or_voice, ask_hba1c)],
        HBA1C: [MessageHandler(text_or_voice, ask_basal_dose)],
        BASAL_DOSE: [MessageHandler(text_or_voice, ask_basal_time)],
        BASAL_TIME: [MessageHandler(text_or_voice, ask_icr)],
        ICR: [MessageHandler(text_or_voice, ask_correction_factor)],
        CORRECTION_FACTOR: [MessageHandler(text_or_voice, ask_target_glucose)],
        TARGET_GLUCOSE: [MessageHandler(text_or_voice, finish_onboarding)],
    },
    fallbacks=[CommandHandler('cancelar', cancel)]
)

log_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('registrar', start_log)],
    states={
        GLUCOSE_STATE: [MessageHandler(text_or_voice, receive_glucose)],
        FOOD_STATE: [MessageHandler(text_or_voice, receive_food)],
        INSULIN_STATE: [MessageHandler(text_or_voice, receive_insulin)],
    },
    fallbacks=[CommandHandler('cancelar', cancel)]
)
