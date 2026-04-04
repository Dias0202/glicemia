# main.py
import asyncio
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from core.config import TELEGRAM_TOKEN, CGM_ENABLED

from handlers.telegram_handlers import (
    onboarding_conv_handler,
    log_conv_handler,
    sensor_conv_handler,
    simulation_conv_handler,
    start,
    menu_callback,
    buscar_alimento,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"GlycemiBot Metabolic Platform is running!")

    def log_message(self, format, *args):
        pass


def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logging.info(f"Health Check na porta {port}")
    server.serve_forever()


async def post_init(application) -> None:
    """Callback executado apos inicializacao do bot."""
    if CGM_ENABLED:
        from tasks.cgm_worker import cgm_sync_loop
        asyncio.create_task(cgm_sync_loop(application))
        logging.info("CGM sync worker agendado")


def main() -> None:
    threading.Thread(target=run_dummy_server, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # Fluxos de conversacao (adicionados primeiro para prioridade)
    application.add_handler(onboarding_conv_handler)
    application.add_handler(log_conv_handler)
    application.add_handler(sensor_conv_handler)
    application.add_handler(simulation_conv_handler)

    # Comandos simples
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('buscar', buscar_alimento))

    # Callbacks do menu principal (menor prioridade)
    application.add_handler(CallbackQueryHandler(
        menu_callback,
        pattern='^cmd_(historico|grafico|ajuda|buscar|menu|score)$'
    ))

    logging.info("Inicializando GlycemiBot - Plataforma de Inteligencia Metabolica...")
    application.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
