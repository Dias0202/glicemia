# handlers/telegram_handlers.py
import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters
)
from services.nlp_service import extract_health_data
from services.calculator_service import calculate_bolus
from services.chart_service import generate_glucose_chart
from repositories.logs_repository import insert_glycemic_log, get_recent_logs, get_logs_for_period
from repositories.user_repository import upsert_user_profile, get_user_profile
from repositories.food_repository import search_food

# Estados para o Onboarding (Metricas do Usuario)
AGE, WEIGHT, HEIGHT, HBA1C, BASAL_DOSE, BASAL_TIME = range(6)

# Estados para o Log Diario
GLUCOSE_STATE, FOOD_STATE, INSULIN_STATE = range(6, 9)

# Estado para busca de alimento
FOOD_SEARCH_STATE = 9


# --- COMANDO /start ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome = (
        "Ola! Eu sou o GlycemiBot, seu assistente de monitoramento glicemico.\n\n"
        "Comandos disponiveis:\n"
        "/perfil - Configurar seu perfil (idade, peso, altura, HbA1c, insulina basal)\n"
        "/registrar - Registrar glicemia, refeicao e insulina\n"
        "/historico - Ver seus ultimos 10 registros\n"
        "/grafico - Gerar grafico glicemico dos ultimos 7 dias\n"
        "/buscar - Buscar alimento na tabela TACO\n"
        "/ajuda - Ver esta mensagem novamente\n"
        "/cancelar - Cancelar operacao em andamento"
    )
    await update.message.reply_text(welcome)


# --- COMANDO /ajuda ---

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "GlycemiBot - Comandos:\n\n"
        "/perfil - Configurar perfil com dados clinicos\n"
        "  Coleta: idade, peso, altura, HbA1c, dose e horario de insulina basal\n\n"
        "/registrar - Novo registro glicemico\n"
        "  Coleta: glicemia atual, refeicao (NLP estima carboidratos), insulina aplicada\n\n"
        "/historico - Ultimos 10 registros com glicemia, carboidratos e insulina\n\n"
        "/grafico - Grafico de tendencia glicemica dos ultimos 7 dias\n\n"
        "/buscar <alimento> - Buscar carboidratos na tabela TACO\n"
        "  Exemplo: /buscar arroz\n\n"
        "/cancelar - Cancelar qualquer operacao em andamento"
    )
    await update.message.reply_text(help_text)


# --- COMANDO /historico ---

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


# --- COMANDO /grafico ---

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


# --- COMANDO /buscar <alimento> ---

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


# --- FLUXO DE ONBOARDING (METRICAS BASE) ---

async def start_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Iniciando configuracao de perfil. Qual a sua idade?")
    return AGE

async def ask_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['age'] = int(update.message.text)
        await update.message.reply_text("Qual o seu peso atual (em kg)?")
        return WEIGHT
    except ValueError:
        await update.message.reply_text("Por favor, insira um numero inteiro valido para a idade.")
        return AGE

async def ask_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['weight'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text("Qual a sua altura (em metros, ex: 1.75)?")
        return HEIGHT
    except ValueError:
        await update.message.reply_text("Formato invalido. Insira o peso em numeros.")
        return WEIGHT

async def ask_hba1c(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['height'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text("Qual o valor da sua ultima hemoglobina glicada (HbA1c)?")
        return HBA1C
    except ValueError:
        await update.message.reply_text("Formato invalido. Insira a altura em metros.")
        return HEIGHT

async def ask_basal_dose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['last_hba1c'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text("Quantas unidades de insulina basal voce aplica diariamente?")
        return BASAL_DOSE
    except ValueError:
        await update.message.reply_text("Formato invalido. Insira o valor numerico da HbA1c.")
        return HBA1C

async def ask_basal_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['basal_dose'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text("Em qual horario voce aplica a insulina basal (ex: 22:00)?")
        return BASAL_TIME
    except ValueError:
        await update.message.reply_text("Formato invalido. Insira o numero de unidades.")
        return BASAL_DOSE

async def finish_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['basal_time'] = update.message.text.strip()

    try:
        upsert_user_profile(
            telegram_user_id=update.message.from_user.id,
            age=context.user_data['age'],
            weight=context.user_data['weight'],
            height=context.user_data['height'],
            last_hba1c=context.user_data['last_hba1c'],
            basal_insulin_dose=context.user_data['basal_dose'],
            basal_insulin_time=context.user_data['basal_time']
        )
        await update.message.reply_text("Perfil configurado e salvo com sucesso no banco de dados.")
    except Exception as e:
        await update.message.reply_text("Falha ao salvar o perfil no banco de dados.")
        logging.error(f"Erro no onboarding: {e}")

    context.user_data.clear()
    return ConversationHandler.END


# --- FLUXO DE LOG DIARIO FRACIONADO ---

async def start_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Iniciando registro. Qual a sua glicemia atual (mg/dL)?")
    return GLUCOSE_STATE

async def receive_glucose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['glucose'] = int(update.message.text)
        await update.message.reply_text(
            "O que voce vai comer agora? (Digite 'nada' caso nao va ingerir alimentos)."
        )
        return FOOD_STATE
    except ValueError:
        await update.message.reply_text("Por favor, insira um valor numerico inteiro para a glicemia.")
        return GLUCOSE_STATE

async def receive_food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    food_text = update.message.text.lower().strip()

    processing_msg = await update.message.reply_text("Processando informacoes nutricionais...")

    if food_text == 'nada':
        context.user_data['carbs'] = 0.0
        suggested_bolus = 0.0
        context.user_data['food_desc'] = "Nenhuma refeicao"
    else:
        try:
            extracted_data = extract_health_data(food_text)
            carbs = extracted_data.get('carbs_ingested', 0.0)
            context.user_data['carbs'] = carbs
            context.user_data['food_desc'] = food_text
            suggested_bolus = calculate_bolus(carbs)
        except Exception as e:
            logging.error(f"Erro NLP: {e}")
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id,
                text="Erro ao extrair dados via NLP. Tente novamente ou insira os carboidratos manualmente."
            )
            return FOOD_STATE

    context.user_data['suggested_bolus'] = suggested_bolus

    response_text = (
        f"Carboidratos estimados: {context.user_data['carbs']} g.\n"
        f"Dose sugerida de insulina rapida (Fator de Carboidrato): {suggested_bolus} U.\n\n"
        f"Quantas unidades voce aplicou de fato?"
    )

    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=processing_msg.message_id,
        text=response_text
    )
    return INSULIN_STATE

async def receive_insulin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        applied_insulin = float(update.message.text.replace(',', '.'))

        insert_glycemic_log(
            telegram_user_id=update.message.from_user.id,
            glucose_level=context.user_data.get('glucose'),
            carbs_ingested=context.user_data.get('carbs'),
            bolus_insulin=applied_insulin,
            refeicao=context.user_data.get('food_desc', 'Nao especificada')
        )

        await update.message.reply_text("Registro finalizado e sincronizado com o Supabase com sucesso.")
        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("Formato invalido. Insira um valor numerico para a insulina aplicada.")
        return INSULIN_STATE


# --- CANCELAR ---

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operacao cancelada.")
    context.user_data.clear()
    return ConversationHandler.END


# --- CONFIGURACAO DOS CONVERSATION HANDLERS ---

onboarding_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('perfil', start_onboarding)],
    states={
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_weight)],
        WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_height)],
        HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_hba1c)],
        HBA1C: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_basal_dose)],
        BASAL_DOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_basal_time)],
        BASAL_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_onboarding)]
    },
    fallbacks=[CommandHandler('cancelar', cancel)]
)

log_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('registrar', start_log)],
    states={
        GLUCOSE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_glucose)],
        FOOD_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_food)],
        INSULIN_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_insulin)]
    },
    fallbacks=[CommandHandler('cancelar', cancel)]
)
