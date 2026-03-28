# repositories/user_repository.py
import logging
from typing import Dict, Any, Optional
from database.supabase_client import supabase_db


def calculate_bmi(weight: float, height: float) -> float:
    """Calcula o Indice de Massa Corporal (IMC)."""
    if height <= 0:
        return 0.0
    if height > 3.0:
        height = height / 100.0
    return round(weight / (height ** 2), 2)


def upsert_user_profile(
    telegram_user_id: int,
    age: int,
    weight: float,
    height: float,
    last_hba1c: float,
    basal_insulin_dose: float,
    basal_insulin_time: str,
    insulin_carb_ratio: float,
    correction_factor: float,
    target_glucose: int = 120
) -> Dict[str, Any]:
    """
    Insere ou atualiza o perfil do usuario com base no telegram_user_id.
    Inclui parametros clinicos para calculo de dose de insulina.
    """
    bmi = calculate_bmi(weight, height)

    data = {
        "telegram_user_id": telegram_user_id,
        "age": age,
        "weight": weight,
        "height": height,
        "bmi": bmi,
        "last_hba1c": last_hba1c,
        "basal_insulin_dose": basal_insulin_dose,
        "basal_insulin_time": basal_insulin_time,
        "insulin_carb_ratio": insulin_carb_ratio,
        "correction_factor": correction_factor,
        "target_glucose": target_glucose,
    }

    try:
        response = supabase_db.table("user_profiles").upsert(
            data, on_conflict="telegram_user_id"
        ).execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        logging.error(f"Erro ao inserir/atualizar perfil do usuario: {e}")
        raise e


def get_user_profile(telegram_user_id: int) -> Optional[Dict[str, Any]]:
    """
    Recupera as metricas do usuario cadastradas no banco de dados.
    """
    try:
        response = supabase_db.table("user_profiles").select("*").eq(
            "telegram_user_id", telegram_user_id
        ).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logging.error(f"Erro ao buscar perfil do usuario: {e}")
        return None
