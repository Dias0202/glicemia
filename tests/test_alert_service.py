# tests/test_alert_service.py
import unittest
from services.alert_service import (
    format_proactive_alert,
    format_metabolic_summary,
    format_glucose_status,
)


class TestFormatProactiveAlert(unittest.TestCase):
    """Testes para formatacao de alertas proativos."""

    def test_urgent_alert(self):
        alert = {"level": "URGENT", "message": "Glicemia critica."}
        text = format_proactive_alert(alert, current_glucose=50, trend_arrow="↓↓")
        self.assertIn("50", text)
        self.assertIn("↓↓", text)
        self.assertIn("15g", text)

    def test_proactive_hypo_alert(self):
        alert = {"level": "PROACTIVE", "message": "Queda prevista."}
        text = format_proactive_alert(
            alert, current_glucose=80, trend_arrow="↓", predicted=55
        )
        self.assertIn("80", text)
        self.assertIn("55", text)
        self.assertIn("lanche", text.lower())

    def test_proactive_hyper_alert(self):
        alert = {"level": "PROACTIVE", "message": "Elevacao prevista."}
        text = format_proactive_alert(
            alert, current_glucose=160, trend_arrow="↑", predicted=210
        )
        self.assertIn("160", text)
        self.assertIn("210", text)
        self.assertIn("caminhada", text.lower())

    def test_warning_alert(self):
        alert = {"level": "WARNING", "message": "Hiperglicemia severa."}
        text = format_proactive_alert(alert, current_glucose=280)
        self.assertIn("280", text)


class TestFormatMetabolicSummary(unittest.TestCase):
    """Testes para formatacao do score metabolico."""

    def test_no_score(self):
        text = format_metabolic_summary({"score": None, "breakdown": {}, "message": "Sem dados"})
        self.assertIn("insuficientes", text.lower())

    def test_good_score(self):
        text = format_metabolic_summary({
            "score": 85,
            "breakdown": {"tir_score": 45, "cv_score": 20, "safety_score": 20},
            "stats": {
                "mean_glucose": 110,
                "time_in_range": 90,
                "cv_percent": 20,
                "time_below_range": 1,
                "std_glucose": 22,
                "readings_count": 100,
                "time_above_range": 9,
            },
            "message": "Excelente controle!",
        })
        self.assertIn("85", text)
        self.assertIn("110", text)
        self.assertIn("Excelente", text)

    def test_score_bar_visual(self):
        text = format_metabolic_summary({
            "score": 70,
            "breakdown": {},
            "stats": {
                "mean_glucose": 130,
                "time_in_range": 60,
                "cv_percent": 30,
                "time_below_range": 5,
                "std_glucose": 39,
                "readings_count": 50,
                "time_above_range": 35,
            },
            "message": "Bom trabalho!",
        })
        self.assertIn("█", text)


class TestFormatGlucoseStatus(unittest.TestCase):
    """Testes para formatacao do status de glicemia."""

    def test_normal_glucose(self):
        text = format_glucose_status(100)
        self.assertIn("100", text)
        self.assertIn("alvo", text.lower())

    def test_low_glucose(self):
        text = format_glucose_status(60)
        self.assertIn("Baixa", text)

    def test_critical_low(self):
        text = format_glucose_status(45)
        self.assertIn("Critica", text)

    def test_high_glucose(self):
        text = format_glucose_status(200)
        self.assertIn("Elevada", text)

    def test_very_high_glucose(self):
        text = format_glucose_status(300)
        self.assertIn("Muito elevada", text)

    def test_with_trend_arrow(self):
        text = format_glucose_status(120, trend_arrow="↑")
        self.assertIn("↑", text)

    def test_with_prediction(self):
        text = format_glucose_status(120, predicted=150)
        self.assertIn("150", text)


if __name__ == '__main__':
    unittest.main()
