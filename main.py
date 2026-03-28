# main.py
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram.ext import Application, CommandHandler
from core.config import TELEGRAM_TOKEN

from handlers.telegram_handlers import (
    onboarding_conv_handler,
    log_conv_handler,
    start,
    ajuda,
    historico,
    grafico,
    buscar_alimento,
)

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
    """Inicializa a aplicacao do bot do Telegram e o servidor web paralelo."""

    threading.Thread(target=run_dummy_server, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Comandos simples
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('ajuda', ajuda))
    application.add_handler(CommandHandler('historico', historico))
    application.add_handler(CommandHandler('grafico', grafico))
    application.add_handler(CommandHandler('buscar', buscar_alimento))

    # Fluxos de conversacao (state machines)
    application.add_handler(onboarding_conv_handler)
    application.add_handler(log_conv_handler)

    logging.info("Inicializando o bot no modo Long Polling...")
    application.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
