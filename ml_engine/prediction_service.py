# ml_engine/prediction_service.py
"""
Motor de predicao glicemica baseado em tendencias.
Implementa extrapolacao linear a partir dos ultimos dados de CGM
e analise de taxa de variacao para alertas proativos.

Nota: Este e o modulo base que sera evoluido para modelos Transformer
(GluFormer/AttenGluco) quando houver dados suficientes de treinamento.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from core.config import (
    HYPO_THRESHOLD, HYPER_THRESHOLD,
    SEVERE_HYPER_THRESHOLD, URGENT_LOW_THRESHOLD
)


def predict_glucose_trend(
    readings: List[Dict[str, Any]],
    horizon_minutes: int = 60,
) -> Optional[Dict[str, Any]]:
    """
    Prediz glicemia futura baseado em tendencia linear dos ultimos dados.

    Args:
        readings: Lista de leituras ordenadas por timestamp (mais antiga primeiro)
                  Cada dict: {"glucose_value": int, "timestamp": str}
        horizon_minutes: Janela de predicao em minutos (padrao 60)

    Returns:
        Dict com predicao ou None se dados insuficientes.
    """
    if len(readings) < 3:
        return None

    # Extrair valores e timestamps
    values = []
    timestamps = []
    for r in readings:
        gv = r.get("glucose_value") or r.get("glucose_level")
        ts = r.get("timestamp")
        if gv is not None and ts is not None:
            values.append(float(gv))
            if isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue
            else:
                dt = ts
            timestamps.append(dt)

    if len(values) < 3:
        return None

    # Converter timestamps em minutos relativos ao primeiro ponto
    t0 = timestamps[0]
    minutes = [(t - t0).total_seconds() / 60.0 for t in timestamps]

    # Regressao linear: y = mx + b
    x = np.array(minutes)
    y = np.array(values)
    n = len(x)
    slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / \
            (n * np.sum(x ** 2) - np.sum(x) ** 2 + 1e-10)
    intercept = (np.sum(y) - slope * np.sum(x)) / n

    # Predicao
    last_minute = minutes[-1]
    predicted_minute = last_minute + horizon_minutes
    predicted_value = round(slope * predicted_minute + intercept, 0)
    predicted_value = max(30, min(500, predicted_value))  # clamp

    # Taxa de variacao (mg/dL por minuto)
    current_value = values[-1]
    rate_of_change = round(slope, 2)  # mg/dL por minuto

    # Classificacao de tendencia
    trend = _classify_trend(rate_of_change)

    # Alertas
    alerts = _generate_alerts(current_value, predicted_value, rate_of_change)

    # Calcular tempo ate atingir limiar critico
    time_to_hypo = _time_to_threshold(current_value, rate_of_change, HYPO_THRESHOLD, "below")
    time_to_hyper = _time_to_threshold(current_value, rate_of_change, HYPER_THRESHOLD, "above")

    return {
        "current_glucose": current_value,
        "predicted_glucose_60m": int(predicted_value),
        "rate_of_change": rate_of_change,
        "trend": trend,
        "trend_arrow": _trend_arrow(trend),
        "alerts": alerts,
        "time_to_hypo_minutes": time_to_hypo,
        "time_to_hyper_minutes": time_to_hyper,
        "confidence": _calculate_confidence(values, slope, intercept, minutes),
        "horizon_minutes": horizon_minutes,
    }


def calculate_metabolic_score(
    readings_24h: List[Dict[str, Any]],
    target_glucose: int = 120,
) -> Dict[str, Any]:
    """
    Calcula pontuacao metabolica (0-100) baseada em:
    - Tempo no alvo (70-180 mg/dL): peso 50%
    - Variabilidade glicemica (CV): peso 25%
    - Ausencia de hipo/hiperglicemias: peso 25%
    """
    if not readings_24h:
        return {"score": None, "breakdown": {}, "message": "Dados insuficientes"}

    values = []
    for r in readings_24h:
        gv = r.get("glucose_value") or r.get("glucose_level")
        if gv is not None:
            values.append(float(gv))

    if len(values) < 5:
        return {"score": None, "breakdown": {}, "message": "Dados insuficientes"}

    n = len(values)
    mean_glucose = np.mean(values)
    std_glucose = np.std(values)
    cv = (std_glucose / mean_glucose * 100) if mean_glucose > 0 else 0

    # Tempo no alvo (70-180)
    in_range = sum(1 for v in values if 70 <= v <= 180)
    tir = (in_range / n) * 100

    # Tempo abaixo do alvo (<70)
    below = sum(1 for v in values if v < 70)
    tbr = (below / n) * 100

    # Tempo acima do alvo (>180)
    above = sum(1 for v in values if v > 180)
    tar = (above / n) * 100

    # Score de tempo no alvo (0-50): TIR >= 70% = maximo
    tir_score = min(50, (tir / 70) * 50)

    # Score de variabilidade (0-25): CV <= 36% = maximo
    cv_score = max(0, 25 - (max(0, cv - 20) / 16) * 25)

    # Score de seguranca (0-25): 0% hipo e 0% hiper = maximo
    safety_score = 25 - (tbr * 0.5 + tar * 0.1)
    safety_score = max(0, min(25, safety_score))

    total = round(tir_score + cv_score + safety_score)
    total = max(0, min(100, total))

    # Mensagem empática
    message = _empathic_score_message(total, tir, tbr)

    return {
        "score": total,
        "breakdown": {
            "tir_score": round(tir_score, 1),
            "cv_score": round(cv_score, 1),
            "safety_score": round(safety_score, 1),
        },
        "stats": {
            "mean_glucose": round(mean_glucose, 1),
            "std_glucose": round(std_glucose, 1),
            "cv_percent": round(cv, 1),
            "time_in_range": round(tir, 1),
            "time_below_range": round(tbr, 1),
            "time_above_range": round(tar, 1),
            "readings_count": n,
        },
        "message": message,
    }


def simulate_meal_impact(
    current_glucose: float,
    carbs: float,
    icr: float,
    correction_factor: float,
    target_glucose: int,
    insulin_dose: float,
    readings_history: Optional[List[Dict]] = None,
) -> List[Dict[str, Any]]:
    """
    Simula impacto de uma refeicao na glicemia ao longo de 4 horas.
    Modelo simplificado baseado em farmacocinética de insulina rapida
    e absorção de carboidratos.

    Retorna lista de pontos simulados a cada 15 minutos.
    """
    points = []
    glucose = current_glucose

    # Parametros fisiologicos simplificados
    carb_absorption_rate = carbs / 120  # g/min (absorção em ~2h)
    insulin_peak_minutes = 75  # pico insulina rapida em ~75min
    insulin_duration = 240  # duracao total 4h

    for t in range(0, 241, 15):
        # Efeito carboidrato: curva gaussiana com pico em ~45min
        carb_effect = carb_absorption_rate * 3.0 * np.exp(-0.5 * ((t - 45) / 30) ** 2)
        carb_glucose_rise = carb_effect * (correction_factor / icr) if icr > 0 else 0

        # Efeito insulina: curva com pico em ~75min
        if insulin_dose > 0 and t > 15:
            insulin_fraction = np.exp(-0.5 * ((t - insulin_peak_minutes) / 50) ** 2)
            insulin_effect = insulin_dose * correction_factor * insulin_fraction * 0.015
        else:
            insulin_effect = 0

        glucose = glucose + carb_glucose_rise - insulin_effect
        glucose = max(40, min(400, glucose))

        points.append({
            "minutes": t,
            "predicted_glucose": round(glucose, 0),
            "is_prediction": True,
        })

    return points


# --- Funcoes auxiliares ---

def _classify_trend(rate: float) -> str:
    if rate < -2.0:
        return "FALLING_FAST"
    elif rate < -1.0:
        return "FALLING"
    elif rate <= 1.0:
        return "STABLE"
    elif rate <= 2.0:
        return "RISING"
    else:
        return "RISING_FAST"


def _trend_arrow(trend: str) -> str:
    arrows = {
        "FALLING_FAST": "↓↓",
        "FALLING": "↓",
        "STABLE": "→",
        "RISING": "↑",
        "RISING_FAST": "↑↑",
    }
    return arrows.get(trend, "?")


def _generate_alerts(current: float, predicted: float, rate: float) -> List[Dict[str, str]]:
    alerts = []

    if current < URGENT_LOW_THRESHOLD:
        alerts.append({
            "level": "URGENT",
            "message": f"URGENTE: Glicemia critica ({int(current)} mg/dL). Ingira carboidratos rapidos imediatamente.",
        })
    elif current < HYPO_THRESHOLD:
        alerts.append({
            "level": "WARNING",
            "message": f"Glicemia baixa ({int(current)} mg/dL). Considere 15g de carboidrato rapido.",
        })

    if predicted < HYPO_THRESHOLD and current >= HYPO_THRESHOLD:
        alerts.append({
            "level": "PROACTIVE",
            "message": (
                f"Sua trajetoria indica queda para ~{int(predicted)} mg/dL na proxima hora. "
                "Considere um lanche leve agora para prevenir hipoglicemia."
            ),
        })

    if predicted > HYPER_THRESHOLD and current <= HYPER_THRESHOLD:
        alerts.append({
            "level": "PROACTIVE",
            "message": (
                f"Predicao indica elevacao para ~{int(predicted)} mg/dL. "
                "Uma caminhada de 10-15 minutos agora pode achatar o pico em ate 30%."
            ),
        })

    if current > SEVERE_HYPER_THRESHOLD:
        alerts.append({
            "level": "WARNING",
            "message": f"Hiperglicemia severa ({int(current)} mg/dL). Considere correcao.",
        })

    return alerts


def _time_to_threshold(current: float, rate: float, threshold: float, direction: str) -> Optional[int]:
    if rate == 0:
        return None
    if direction == "below" and rate >= 0:
        return None
    if direction == "above" and rate <= 0:
        return None

    minutes = (threshold - current) / rate
    if minutes <= 0:
        return None
    if minutes > 360:
        return None
    return round(minutes)


def _calculate_confidence(values, slope, intercept, minutes) -> float:
    """R-squared como medida de confianca da predicao linear."""
    y = np.array(values)
    y_pred = slope * np.array(minutes) + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    if ss_tot == 0:
        return 1.0
    r2 = max(0, 1 - ss_res / ss_tot)
    return round(r2, 2)


def _empathic_score_message(score: int, tir: float, tbr: float) -> str:
    if score >= 85:
        return "Excelente controle! Voce esta no caminho certo para sua saude metabolica."
    elif score >= 70:
        return "Bom trabalho! Seu controle esta acima da media. Continue assim."
    elif score >= 50:
        msg = "Progresso solido. "
        if tbr > 5:
            msg += "Atencao especial aos episodios de hipoglicemia."
        elif tir < 50:
            msg += "Tente manter mais tempo na faixa alvo (70-180)."
        else:
            msg += "Pequenos ajustes podem fazer grande diferenca."
        return msg
    else:
        return "Cada dia e uma nova oportunidade. Pequenos passos levam a grandes resultados."
