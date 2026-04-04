# repositories/sensor_repository.py
"""
CRUD para a tabela sensor_integrations.
Armazena credenciais criptografadas do LibreLinkUp para cada usuario.
"""
import logging
from typing import Dict, Any, Optional, List
from database.supabase_client import supabase_db
from core.security import encrypt_value, decrypt_value


def upsert_sensor_integration(
    telegram_user_id: int,
    llu_email: str,
    llu_password: str,
    llu_region_code: str = "BR",
) -> Dict[str, Any]:
    """Insere ou atualiza integracao de sensor para o usuario."""
    data = {
        "telegram_user_id": telegram_user_id,
        "llu_email": llu_email,
        "llu_password_hash": encrypt_value(llu_password),
        "llu_region_code": llu_region_code.upper(),
        "status": "ACTIVE",
    }
    try:
        response = supabase_db.table("sensor_integrations").upsert(
            data, on_conflict="telegram_user_id"
        ).execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        logging.error(f"Erro ao salvar integracao sensor: {e}")
        raise


def get_sensor_integration(telegram_user_id: int) -> Optional[Dict[str, Any]]:
    """Recupera integracao de sensor do usuario (com senha descriptografada)."""
    try:
        response = (
            supabase_db.table("sensor_integrations")
            .select("*")
            .eq("telegram_user_id", telegram_user_id)
            .eq("status", "ACTIVE")
            .execute()
        )
        if not response.data:
            return None
        record = response.data[0]
        record["llu_password"] = decrypt_value(record["llu_password_hash"])
        return record
    except Exception as e:
        logging.error(f"Erro ao buscar integracao sensor: {e}")
        return None


def get_all_active_integrations() -> List[Dict[str, Any]]:
    """Retorna todas as integracoes ativas (para o worker de sincronizacao)."""
    try:
        response = (
            supabase_db.table("sensor_integrations")
            .select("*")
            .eq("status", "ACTIVE")
            .execute()
        )
        records = response.data if response.data else []
        for r in records:
            try:
                r["llu_password"] = decrypt_value(r["llu_password_hash"])
            except ValueError:
                r["llu_password"] = None
                r["status"] = "ERROR"
        return records
    except Exception as e:
        logging.error(f"Erro ao buscar integracoes ativas: {e}")
        return []


def update_sync_status(
    telegram_user_id: int,
    last_sync_timestamp: str,
    llu_patient_uuid: Optional[str] = None,
    llu_token_jwt: Optional[str] = None,
) -> None:
    """Atualiza timestamp de sincronizacao e tokens."""
    data = {"last_sync_timestamp": last_sync_timestamp}
    if llu_patient_uuid:
        data["llu_patient_uuid"] = llu_patient_uuid
    if llu_token_jwt:
        data["llu_token_jwt"] = llu_token_jwt
    try:
        supabase_db.table("sensor_integrations").update(data).eq(
            "telegram_user_id", telegram_user_id
        ).execute()
    except Exception as e:
        logging.error(f"Erro ao atualizar sync status: {e}")


def deactivate_sensor_integration(telegram_user_id: int) -> None:
    """Desativa integracao de sensor."""
    try:
        supabase_db.table("sensor_integrations").update(
            {"status": "INACTIVE"}
        ).eq("telegram_user_id", telegram_user_id).execute()
    except Exception as e:
        logging.error(f"Erro ao desativar integracao: {e}")
