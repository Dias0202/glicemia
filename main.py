# main.py
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram.ext import Application
from core.config import TELEGRAM_TOKEN

# Importação correta dos novos fluxos de conversação
from handlers.telegram_handlers import onboarding_conv_handler, log_conv_handler

# Configuração do módulo de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Servidor web minimalista para responder aos health checks do Render."""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")
        
    def log_message(self, format, *args):
        pass

def run_dummy_server():
    """Inicializa o servidor HTTP na porta definida pelo Render."""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logging.info(f"Servidor de Health Check iniciado na porta {port}")
    server.serve_forever()

def main() -> None:
    """Inicializa a aplicação do bot do Telegram e o servidor web paralelo."""
    
    # Inicia o servidor dummy em uma thread separada
    threading.Thread(target=run_dummy_server, daemon=True).start()

    # Configuração da aplicação do Telegram
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Adição dos novos manipuladores de estado (Onboarding e Registro Diário)
    application.add_handler(onboarding_conv_handler)
    application.add_handler(log_conv_handler)

    # Execução via Long Polling
    logging.info("Inicializando o bot no modo Long Polling...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()