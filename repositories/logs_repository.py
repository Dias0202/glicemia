# repositories/logs_repository.py
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from database.supabase_client import supabase_db
import logging

def insert_glycemic_log(
    glucose_level: Optional[int] = None,
    carbs_ingested: Optional[float] = None,
    bolus_insulin: Optional[float] = None,
    basal_insulin: Optional[float] = None,
    exercise_done: bool = False,
    exercise_intensity: Optional[str] = None,
    mood: Optional[str] = None,
    refeicao: str = "Não especificada",
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Insere um novo registro na tabela glycemic_logs no Supabase.
    """
    # Define o timestamp atual no formato ISO 8601 (com fuso horário UTC) se não for fornecido
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()

    data = {
        "timestamp": timestamp,
        "glucose_level": glucose_level,
        "carbs_ingested": carbs_ingested,
        "bolus_insulin": bolus_insulin,
        "basal_insulin": basal_insulin,
        "exercise_done": exercise_done,
        "exercise_intensity": exercise_intensity,
        "mood": mood,
        "refeicao": refeicao
    }

    # Remove chaves com valores None para enviar apenas dados preenchidos ao Supabase
    data_to_insert = {k: v for k, v in data.items() if v is not None}

    try:
        response = supabase_db.table("glycemic_logs").insert(data_to_insert).execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        logging.error(f"Erro ao inserir log glicêmico: {e}")
        raise e