# services/calculator_service.py
import logging
from typing import Dict


def calculate_carb_bolus(carbs_ingested: float, insulin_carb_ratio: float) -> float:
    """
    Calcula o bolus alimentar (cobertura de carboidratos).
    Formula: dose = carboidratos / razao insulina-carboidrato (ICR)
    Exemplo: 60g carbs / ICR 10 = 6 U
    """
    if not carbs_ingested or carbs_ingested <= 0:
        return 0.0
    if not insulin_carb_ratio or insulin_carb_ratio <= 0:
        return 0.0
    return round(carbs_ingested / insulin_carb_ratio, 2)


def calculate_correction_dose(
    current_glucose: int,
    target_glucose: int,
    correction_factor: float
) -> float:
    """
    Calcula a dose de correcao para trazer a glicemia ao alvo.
    Formula: dose = (glicemia_atual - glicemia_alvo) / fator_de_correcao
    So aplica se glicemia atual > alvo.
    Exemplo: (250 - 120) / 50 = 2.6 U
    """
    if not current_glucose or not correction_factor or correction_factor <= 0:
        return 0.0
    if current_glucose <= target_glucose:
        return 0.0
    return round((current_glucose - target_glucose) / correction_factor, 2)


def calculate_total_dose(
    carbs_ingested: float,
    current_glucose: int,
    insulin_carb_ratio: float,
    correction_factor: float,
    target_glucose: int = 120
) -> Dict[str, float]:
    """
    Calcula a dose total de insulina rapida recomendada.
    Retorna um dicionario detalhado com cada componente do calculo.

    Componentes:
      - bolus_alimentar: cobertura dos carboidratos ingeridos
      - dose_correcao: correcao da hiperglicemia (se acima do alvo)
      - dose_total: soma dos dois componentes
    """
    bolus = calculate_carb_bolus(carbs_ingested, insulin_carb_ratio)
    correction = calculate_correction_dose(current_glucose, target_glucose, correction_factor)
    total = round(bolus + correction, 2)

    return {
        "bolus_alimentar": bolus,
        "dose_correcao": correction,
        "dose_total": total,
        "carbs_ingested": carbs_ingested or 0.0,
        "current_glucose": current_glucose or 0,
        "target_glucose": target_glucose,
        "insulin_carb_ratio": insulin_carb_ratio,
        "correction_factor": correction_factor,
    }
