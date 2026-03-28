# services/chart_service.py
import io
import logging
from typing import List, Dict, Any
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def generate_glucose_chart(logs: List[Dict[str, Any]]) -> io.BytesIO:
    """
    Gera um grafico de linha da glicemia ao longo do tempo.
    Retorna a imagem como buffer em memoria (BytesIO) pronto para envio via Telegram.
    """
    timestamps = []
    glucose_values = []

    for log in logs:
        if log.get("glucose_level") is not None and log.get("timestamp"):
            ts = log["timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            timestamps.append(ts)
            glucose_values.append(log["glucose_level"])

    if not glucose_values:
        raise ValueError("Sem dados de glicemia para gerar o grafico.")

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(timestamps, glucose_values, marker='o', color='#2196F3', linewidth=2, markersize=5)

    # Faixas de referencia
    ax.axhspan(70, 140, alpha=0.1, color='green', label='Faixa alvo (70-140)')
    ax.axhline(y=70, color='orange', linestyle='--', alpha=0.5, linewidth=0.8)
    ax.axhline(y=140, color='orange', linestyle='--', alpha=0.5, linewidth=0.8)
    ax.axhline(y=180, color='red', linestyle='--', alpha=0.5, linewidth=0.8)

    ax.set_xlabel('Data/Hora', fontsize=11)
    ax.set_ylabel('Glicemia (mg/dL)', fontsize=11)
    ax.set_title('Historico Glicemico', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    fig.autofmt_xdate(rotation=30)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120)
    buf.seek(0)
    plt.close(fig)

    return buf
