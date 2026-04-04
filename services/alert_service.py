# services/alert_service.py
"""
Servico de alertas proativos e empaticos.
Substitui alertas clinicos frios por mensagens orientadas a acao
seguindo o principio de interceptacao de momentum.
"""
from typing import Dict, Any, Optional


def format_proactive_alert(
    alert: Dict[str, str],
    current_glucose: int,
    trend_arrow: str = "",
    predicted: Optional[int] = None,
) -> str:
    """
    Formata alerta com tom empatico e orientado a acao.
    Em vez de "Glicemia alta - Cuidado", oferece acao curativa.
    """
    level = alert.get("level", "INFO")
    base_msg = alert.get("message", "")

    if level == "URGENT":
        return (
            f"🚨 {base_msg}\n\n"
            f"Glicemia atual: {current_glucose} mg/dL {trend_arrow}\n"
            "Ingira 15g de carboidrato rapido (suco, mel, pastilha de glicose) "
            "e aguarde 15 minutos para verificar novamente."
        )

    if level == "PROACTIVE" and predicted:
        if predicted < 70:
            return (
                f"📊 Tendencia detectada {trend_arrow}\n\n"
                f"Atual: {current_glucose} mg/dL → Previsao: ~{predicted} mg/dL\n\n"
                f"{base_msg}\n\n"
                "💡 Sugestao: um lanche leve com 15-20g de carboidratos "
                "agora pode estabilizar sua glicemia."
            )
        else:
            return (
                f"📊 Tendencia detectada {trend_arrow}\n\n"
                f"Atual: {current_glucose} mg/dL → Previsao: ~{predicted} mg/dL\n\n"
                f"{base_msg}\n\n"
                "💡 10 minutos de caminhada ou 25 agachamentos agora "
                "podem amplificar sua sensibilidade a insulina muscular "
                "e reduzir o pico previsto em ate 30%."
            )

    if level == "WARNING":
        return (
            f"⚠️ Atencao\n\n"
            f"Atual: {current_glucose} mg/dL {trend_arrow}\n"
            f"{base_msg}"
        )

    return f"ℹ️ {current_glucose} mg/dL {trend_arrow}\n{base_msg}"


def format_metabolic_summary(score_data: Dict[str, Any]) -> str:
    """Formata resumo do score metabolico para exibicao no bot."""
    score = score_data.get("score")
    if score is None:
        return "📊 Score metabolico: dados insuficientes\nContinue registrando para acompanhar sua evolucao!"

    stats = score_data.get("stats", {})
    message = score_data.get("message", "")

    # Barra visual
    filled = round(score / 10)
    bar = "█" * filled + "░" * (10 - filled)

    emoji = "🟢" if score >= 70 else "🟡" if score >= 50 else "🔴"

    text = (
        f"{emoji} Score Metabolico: {score}/100\n"
        f"[{bar}]\n\n"
        f"📈 Glicemia media: {stats.get('mean_glucose', '-')} mg/dL\n"
        f"⏱ Tempo no alvo: {stats.get('time_in_range', '-')}%\n"
        f"📉 Variabilidade (CV): {stats.get('cv_percent', '-')}%\n"
        f"⚠️ Abaixo do alvo: {stats.get('time_below_range', '-')}%\n"
        f"📊 Leituras: {stats.get('readings_count', 0)}\n\n"
        f"{message}"
    )
    return text


def format_glucose_status(
    glucose: int,
    trend_arrow: str = "",
    predicted: Optional[int] = None,
) -> str:
    """Formata status atual da glicemia com tendencia."""
    # Emoji baseado na faixa
    if glucose < 54:
        emoji = "🔴"
        status = "Critica baixa"
    elif glucose < 70:
        emoji = "🟠"
        status = "Baixa"
    elif glucose <= 180:
        emoji = "🟢"
        status = "No alvo"
    elif glucose <= 250:
        emoji = "🟡"
        status = "Elevada"
    else:
        emoji = "🔴"
        status = "Muito elevada"

    text = f"{emoji} {glucose} mg/dL {trend_arrow} ({status})"

    if predicted:
        text += f"\nPrevisao 1h: ~{predicted} mg/dL"

    return text
