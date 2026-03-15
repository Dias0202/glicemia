# main.py
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from core.config import TELEGRAM_TOKEN
from handlers.telegram_handlers import start_command, help_command, handle_text_message

# Configuração do módulo de logging para monitoramento de execução
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main() -> None:
    """Inicializa a aplicação do bot do Telegram e inicia o loop de eventos."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Roteamento de comandos e mensagens
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Execução via Long Polling
    logging.info("Inicializando o bot no modo Long Polling...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()