# repositories/logs_repository.py
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from database.supabase_client import supabase_db
import logging

def insert_glycemic_log(
    telegram_user_id: int,
    glucose_level: Optional[int] = None,
    carbs_ingested: Optional[float] = None,
    bolus_insulin: Optional[float] = None,
    basal_insulin: Optional[float] = None,
    exercise_done: bool = False,
    exercise_intensity: Optional[str] = None,
    mood: Optional[str] = None,
    refeicao: str = "Não especificada",
    timestamp: Optional[str] = None,
    source_type: str = "MANUAL",
    trend_arrow: Optional[str] = None,
    predicted_glucose_60m: Optional[int] = None,
    ai_recommendation: Optional[str] = None,
    heart_rate_bpm: Optional[int] = None,
    is_synthetic: bool = False,
) -> Dict[str, Any]:
    """
    Insere um novo registro na tabela glycemic_logs no Supabase.
    Suporta campos expandidos para dados CGM e predicoes de IA.
    """
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()

    data = {
        "telegram_user_id": telegram_user_id,
        "timestamp": timestamp,
        "glucose_level": glucose_level,
        "carbs_ingested": carbs_ingested,
        "bolus_insulin": bolus_insulin,
        "basal_insulin": basal_insulin,
        "exercise_done": exercise_done,
        "exercise_intensity": exercise_intensity,
        "mood": mood,
        "refeicao": refeicao,
        "source_type": source_type,
        "trend_arrow": trend_arrow,
        "predicted_glucose_60m": predicted_glucose_60m,
        "ai_recommendation": ai_recommendation,
        "heart_rate_bpm": heart_rate_bpm,
        "is_synthetic": is_synthetic,
    }

    data_to_insert = {k: v for k, v in data.items() if v is not None}

    try:
        response = supabase_db.table("glycemic_logs").insert(data_to_insert).execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        logging.error(f"Erro ao inserir log glicêmico: {e}")
        raise e


def get_recent_logs(telegram_user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retorna os registros glicêmicos mais recentes do usuário.
    """
    try:
        response = (
            supabase_db.table("glycemic_logs")
            .select("*")
            .eq("telegram_user_id", telegram_user_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        logging.error(f"Erro ao buscar logs recentes: {e}")
        return []


def get_logs_for_period(telegram_user_id: int, days: int = 7) -> List[Dict[str, Any]]:
    """
    Retorna os registros glicêmicos de um período (em dias) para geração de gráficos.
    """
    try:
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        response = (
            supabase_db.table("glycemic_logs")
            .select("*")
            .eq("telegram_user_id", telegram_user_id)
            .gte("timestamp", start_date)
            .order("timestamp", desc=False)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        logging.error(f"Erro ao buscar logs do período: {e}")
        return []