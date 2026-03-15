# services/calculator_service.py
import logging
from core.config import CARB_FACTOR

def calculate_bolus(carbs_ingested: float) -> float:
    """
    Calcula a dose sugerida de insulina bolus com base na ingestao de carboidratos
    e no fator de carboidrato configurado.
    """
    if not carbs_ingested or carbs_ingested <= 0:
        return 0.0
    
    try:
        suggested_dose = carbs_ingested / CARB_FACTOR
        return round(suggested_dose, 2)
    except Exception as e:
        logging.error(f"Erro ao calcular insulina bolus: {e}")
        return 0.0