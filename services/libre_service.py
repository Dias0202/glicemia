# services/libre_service.py
"""
Servico de integracao com FreeStyle Libre 2 Plus via LibreLinkUp API.
Utiliza a biblioteca pylibrelinkup para autenticacao e coleta de dados CGM.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

try:
    from pylibrelinkup import PyLibreLinkUp
    HAS_PYLIBRELINKUP = True
except ImportError:
    HAS_PYLIBRELINKUP = False

# Mapeamento de regioes para endpoints da Abbott
REGION_ENDPOINTS = {
    "BR": "api-br.libreview.io",
    "US": "api-us.libreview.io",
    "EU": "api-eu.libreview.io",
    "DE": "api-de.libreview.io",
    "FR": "api-fr.libreview.io",
    "JP": "api-jp.libreview.io",
    "AP": "api-ap.libreview.io",
    "AU": "api-au.libreview.io",
}


def create_client(email: str, password: str, region: str = "BR") -> Optional[Any]:
    """Cria e autentica um cliente LibreLinkUp."""
    if not HAS_PYLIBRELINKUP:
        logging.error("pylibrelinkup nao instalado")
        return None

    url = REGION_ENDPOINTS.get(region.upper(), REGION_ENDPOINTS["US"])
    try:
        client = PyLibreLinkUp(email=email, password=password, url=url)
        client.authenticate()
        return client
    except Exception as e:
        logging.error(f"Erro autenticacao LibreLinkUp [{region}]: {e}")
        return None


def get_patient_id(client) -> Optional[str]:
    """Recupera o UUID do paciente conectado."""
    try:
        patients = client.get_patients()
        if patients:
            return str(patients[0].patient_id)
        return None
    except Exception as e:
        logging.error(f"Erro ao buscar pacientes: {e}")
        return None


def get_latest_glucose(client) -> Optional[Dict[str, Any]]:
    """Obtem a leitura de glicose mais recente do CGM."""
    try:
        patients = client.get_patients()
        if not patients:
            return None

        patient = patients[0]
        latest = client.get_latest_reading(patient.patient_id)
        if not latest:
            return None

        return {
            "glucose_value": latest.value,
            "trend_arrow": _map_trend(getattr(latest, 'trend', None)),
            "timestamp": latest.timestamp.isoformat() if hasattr(latest, 'timestamp') else datetime.now(timezone.utc).isoformat(),
            "source_type": "LIBRELINKUP_CLOUD",
            "is_high": getattr(latest, 'is_high', False),
            "is_low": getattr(latest, 'is_low', False),
        }
    except Exception as e:
        logging.error(f"Erro ao obter leitura CGM: {e}")
        return None


def get_glucose_history(client, hours: int = 12) -> List[Dict[str, Any]]:
    """Obtem historico de leituras das ultimas N horas."""
    try:
        patients = client.get_patients()
        if not patients:
            return []

        patient = patients[0]
        graph_data = client.get_graph(patient.patient_id)
        if not graph_data:
            return []

        readings = []
        for point in graph_data:
            readings.append({
                "glucose_value": point.value,
                "timestamp": point.timestamp.isoformat() if hasattr(point, 'timestamp') else None,
                "source_type": "LIBRELINKUP_CLOUD",
            })
        return readings
    except Exception as e:
        logging.error(f"Erro ao obter historico CGM: {e}")
        return []


def validate_credentials(email: str, password: str, region: str = "BR") -> Dict[str, Any]:
    """Valida credenciais do LibreLinkUp e retorna status."""
    client = create_client(email, password, region)
    if client is None:
        return {"valid": False, "error": "Falha na autenticacao"}

    patient_id = get_patient_id(client)
    if not patient_id:
        return {"valid": False, "error": "Nenhum paciente encontrado. Verifique o LibreLinkUp."}

    latest = get_latest_glucose(client)
    return {
        "valid": True,
        "patient_id": patient_id,
        "latest_glucose": latest,
    }


def _map_trend(trend_value) -> str:
    """Mapeia valor numerico de tendencia para seta descritiva."""
    trend_map = {
        1: "FALLING_FAST",
        2: "FALLING",
        3: "STABLE",
        4: "RISING",
        5: "RISING_FAST",
    }
    if trend_value is None:
        return "UNKNOWN"
    if isinstance(trend_value, int):
        return trend_map.get(trend_value, "UNKNOWN")
    return str(trend_value)
