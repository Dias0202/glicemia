# tasks/cgm_worker.py
"""
Worker assincrono para sincronizacao periodica de dados CGM.
Puxa dados do LibreLinkUp para cada usuario com integracao ativa,
executa predicoes e envia alertas proativos via Telegram.
"""
import asyncio
import logging
import random
from datetime import datetime, timezone

from core.config import CGM_SYNC_INTERVAL_MINUTES, CGM_ENABLED
from services.libre_service import create_client, get_latest_glucose, get_glucose_history
from repositories.sensor_repository import (
    get_all_active_integrations,
    update_sync_status,
)
from repositories.logs_repository import insert_glycemic_log
from ml_engine.prediction_service import predict_glucose_trend, calculate_metabolic_score
from services.alert_service import format_proactive_alert


async def cgm_sync_loop(application) -> None:
    """
    Loop principal do worker CGM.
    Roda como task asyncio dentro do event loop do telegram bot.
    """
    if not CGM_ENABLED:
        logging.info("CGM worker desativado (CGM_ENABLED=false)")
        return

    logging.info(f"CGM worker iniciado (intervalo: {CGM_SYNC_INTERVAL_MINUTES}min)")

    while True:
        try:
            await _sync_all_users(application)
        except Exception as e:
            logging.error(f"Erro no ciclo CGM worker: {e}")

        # Jitter de 10-30% para evitar rate limiting
        jitter = random.uniform(0.9, 1.3)
        await asyncio.sleep(CGM_SYNC_INTERVAL_MINUTES * 60 * jitter)


async def _sync_all_users(application) -> None:
    """Sincroniza dados de todos os usuarios com integracao ativa."""
    integrations = get_all_active_integrations()
    if not integrations:
        return

    logging.info(f"Sincronizando {len(integrations)} integracao(oes) CGM...")

    for integration in integrations:
        if integration.get("status") == "ERROR" or not integration.get("llu_password"):
            continue

        try:
            await _sync_user(application, integration)
        except Exception as e:
            logging.error(
                f"Erro sync usuario {integration['telegram_user_id']}: {e}"
            )
        # Delay entre usuarios para evitar rate limit
        await asyncio.sleep(2)


async def _sync_user(application, integration: dict) -> None:
    """Sincroniza dados de um usuario especifico."""
    user_id = integration["telegram_user_id"]
    email = integration["llu_email"]
    password = integration["llu_password"]
    region = integration.get("llu_region_code", "BR")

    client = create_client(email, password, region)
    if not client:
        logging.warning(f"Falha auth CGM para usuario {user_id}")
        return

    # Obter leitura mais recente
    latest = get_latest_glucose(client)
    if not latest:
        return

    # Salvar no banco
    try:
        insert_glycemic_log(
            telegram_user_id=user_id,
            glucose_level=latest["glucose_value"],
            timestamp=latest["timestamp"],
            source_type=latest.get("source_type", "LIBRELINKUP_CLOUD"),
            trend_arrow=latest.get("trend_arrow"),
        )
    except Exception as e:
        logging.error(f"Erro ao salvar leitura CGM user {user_id}: {e}")

    # Atualizar timestamp de sync
    update_sync_status(
        telegram_user_id=user_id,
        last_sync_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Obter historico para predicao
    history = get_glucose_history(client, hours=3)
    if len(history) >= 3:
        prediction = predict_glucose_trend(history, horizon_minutes=60)
        if prediction and prediction.get("alerts"):
            # Enviar alertas proativos via Telegram
            for alert in prediction["alerts"]:
                try:
                    text = format_proactive_alert(
                        alert,
                        current_glucose=latest["glucose_value"],
                        trend_arrow=prediction.get("trend_arrow", ""),
                        predicted=prediction.get("predicted_glucose_60m"),
                    )
                    await application.bot.send_message(
                        chat_id=user_id,
                        text=text,
                    )
                except Exception as e:
                    logging.error(f"Erro ao enviar alerta user {user_id}: {e}")
