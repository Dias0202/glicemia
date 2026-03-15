# main.py
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from core.config import TELEGRAM_TOKEN
from handlers.telegram_handlers import start_command, help_command, handle_text_message

# Configuração do módulo de logging para monitoramento de execução
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """
    Servidor web minimalista para responder aos health checks do Render 
    e aos pings do UptimeRobot.
    """
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")
        
    def log_message(self, format, *args):
        # Suprime os logs de requisições HTTP para não poluir o terminal do bot
        pass

def run_dummy_server():
    """
    Inicializa o servidor HTTP na porta definida pelo Render.
    """
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logging.info(f"Servidor de Health Check iniciado na porta {port}")
    server.serve_forever()

def main() -> None:
    """Inicializa a aplicação do bot do Telegram e o servidor web paralelo."""
    
    # Inicia o servidor dummy em uma thread separada (daemon=True garante 
    # que ele encerre quando o bot principal parar)
    threading.Thread(target=run_dummy_server, daemon=True).start()

    # Configuração da aplicação do Telegram
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