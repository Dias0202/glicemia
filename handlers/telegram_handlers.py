# handlers/telegram_handlers.py
import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.nlp_service import extract_health_data
from services.calculator_service import calculate_bolus
from repositories.logs_repository import insert_glycemic_log

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde ao comando /start."""
    await update.message.reply_text(
        "Bot de monitoramento glicemico iniciado. Envie um relato em texto natural "
        "sobre sua glicemia, alimentacao, insulina, exercicios e humor."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde ao comando /help."""
    await update.message.reply_text(
        "Para registrar dados, envie uma mensagem natural. Exemplo:\n"
        "'Glicemia 100, comi 30g de carbo, tomei 2u de rapida. Fui treinar.'"
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa mensagens de texto utilizando a API do Groq e insere no banco de dados."""
    user_text = update.message.text
    
    # Feedback inicial para o usuário
    processing_message = await update.message.reply_text("Processando informações e extraindo dados...")
    
    try:
        # Extração de dados via NLP (Groq)
        extracted_data = extract_health_data(user_text)
        
        # Obtenção dos carboidratos para cálculo de sugestão, se necessário
        carbs = extracted_data.get("carbs_ingested")
        suggested_bolus = 0.0
        if carbs:
            suggested_bolus = calculate_bolus(carbs)
        
        # Inserção no banco de dados (Supabase)
        insert_glycemic_log(
            glucose_level=extracted_data.get("glucose_level"),
            carbs_ingested=carbs,
            bolus_insulin=extracted_data.get("bolus_insulin"),
            basal_insulin=extracted_data.get("basal_insulin"),
            exercise_done=extracted_data.get("exercise_done", False),
            exercise_intensity=extracted_data.get("exercise_intensity"),
            mood=extracted_data.get("mood"),
            refeicao=extracted_data.get("refeicao", "Não especificada")
        )
        
        # Formatação estruturada da resposta de confirmação
        response_text = "Registro salvo no banco de dados com sucesso.\n\nDados extraídos e armazenados:\n"
        response_text += f"- Glicemia: {extracted_data.get('glucose_level')} mg/dL\n"
        response_text += f"- Carboidratos: {carbs} g\n"
        response_text += f"- Insulina Bolus Aplicada: {extracted_data.get('bolus_insulin')} U\n"
        response_text += f"- Insulina Basal Aplicada: {extracted_data.get('basal_insulin')} U\n"
        response_text += f"- Exercício: {'Sim' if extracted_data.get('exercise_done') else 'Não'}\n"
        response_text += f"- Intensidade: {extracted_data.get('exercise_intensity')}\n"
        response_text += f"- Humor: {extracted_data.get('mood')}\n"
        response_text += f"- Refeição: {extracted_data.get('refeicao')}\n"
        
        # Adiciona a sugestão de cálculo apenas se carboidratos foram ingeridos e a insulina bolus não foi explicitamente declarada
        if carbs and not extracted_data.get("bolus_insulin"):
            response_text += f"\nSugestão de Bolus Calculada (Fator configurado): {suggested_bolus} U"
            
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=processing_message.message_id,
            text=response_text
        )

    except Exception as e:
        logging.error(f"Erro na execução do pipeline de mensagem: {e}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=processing_message.message_id,
            text="Ocorreu um erro técnico ao processar a mensagem. Verifique os logs do sistema."
        )