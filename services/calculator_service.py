# services/calculator_service.py
from typing import Dict

# Fator de reducao de dose de insulina por intensidade de exercicio.
# Exercicio aumenta sensibilidade a insulina -> necessidade menor de dose.
EXERCISE_FACTORS = {
    "nenhum": 1.0,
    "leve": 0.90,       # caminhada, yoga -> reduz 10%
    "moderado": 0.80,   # corrida leve, bike -> reduz 20%
    "intenso": 0.70,    # crossfit, HIIT, musculacao pesada -> reduz 30%
}


def calculate_carb_bolus(carbs_ingested: float, insulin_carb_ratio: float) -> float:
    """
    Bolus alimentar = carboidratos / ICR
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
    Dose de correcao = (glicemia_atual - alvo) / fator_correcao
    So aplica se glicemia > alvo.
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
    target_glucose: int = 120,
    exercise_intensity: str = "nenhum",
) -> Dict[str, float]:
    """
    Calcula a dose total de insulina rapida recomendada.
    Aplica reducao pelo fator de exercicio se aplicavel.
    """
    bolus = calculate_carb_bolus(carbs_ingested, insulin_carb_ratio)
    correction = calculate_correction_dose(current_glucose, target_glucose, correction_factor)
    subtotal = round(bolus + correction, 2)

    ex_factor = EXERCISE_FACTORS.get(exercise_intensity, 1.0)
    total = round(subtotal * ex_factor, 2)
    reduction = round(subtotal - total, 2)

    return {
        "bolus_alimentar": bolus,
        "dose_correcao": correction,
        "subtotal": subtotal,
        "exercise_intensity": exercise_intensity,
        "exercise_factor": ex_factor,
        "exercise_reduction": reduction,
        "dose_total": total,
        "carbs_ingested": carbs_ingested or 0.0,
        "current_glucose": current_glucose or 0,
        "target_glucose": target_glucose,
        "insulin_carb_ratio": insulin_carb_ratio,
        "correction_factor": correction_factor,
    }
