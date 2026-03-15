# handlers/telegram_handlers.py
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from services.nlp_service import extract_health_data
from services.calculator_service import calculate_bolus
from repositories.logs_repository import insert_glycemic_log
from repositories.user_repository import upsert_user_profile

# Definicao de Estados para o Onboarding (Metricas do Usuario)
AGE, WEIGHT, HEIGHT, HBA1C, BASAL_DOSE, BASAL_TIME = range(6)

# Definicao de Estados para o Log Diario
GLUCOSE_STATE, FOOD_STATE, INSULIN_STATE = range(6, 9)

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
        await update.message.reply_text("O que voce vai comer agora? (Digite 'nada' caso nao va ingerir alimentos).")
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
            # Utiliza a IA apenas para extrair as informacoes da refeicao
            extracted_data = extract_health_data(food_text)
            carbs = extracted_data.get('carbs_ingested', 0.0)
            context.user_data['carbs'] = carbs
            context.user_data['food_desc'] = food_text
            suggested_bolus = calculate_bolus(carbs)
        except Exception as e:
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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operacao cancelada.")
    context.user_data.clear()
    return ConversationHandler.END


# --- CONFIGURACAO DOS CONVERSATION HANDLERS (A SER IMPORTADO NO MAIN.PY) ---

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