# tests/test_calculator_service.py
import unittest
from services.calculator_service import (
    calculate_carb_bolus,
    calculate_correction_dose,
    calculate_total_dose,
)


class TestCalculateCarbBolus(unittest.TestCase):
    """Testes para o calculo de bolus alimentar."""

    def test_bolus_normal(self):
        # 60g carbs / ICR 10 = 6.0 U
        self.assertEqual(calculate_carb_bolus(60.0, 10.0), 6.0)

    def test_bolus_icr_15(self):
        # 45g / ICR 15 = 3.0 U
        self.assertEqual(calculate_carb_bolus(45.0, 15.0), 3.0)

    def test_bolus_zero_carbs(self):
        self.assertEqual(calculate_carb_bolus(0.0, 10.0), 0.0)

    def test_bolus_negative_carbs(self):
        self.assertEqual(calculate_carb_bolus(-5.0, 10.0), 0.0)

    def test_bolus_none_carbs(self):
        self.assertEqual(calculate_carb_bolus(None, 10.0), 0.0)

    def test_bolus_zero_icr(self):
        self.assertEqual(calculate_carb_bolus(50.0, 0.0), 0.0)

    def test_bolus_rounding(self):
        # 33g / ICR 10 = 3.3 U
        self.assertEqual(calculate_carb_bolus(33.0, 10.0), 3.3)


class TestCalculateCorrectionDose(unittest.TestCase):
    """Testes para o calculo de dose de correcao."""

    def test_correction_above_target(self):
        # (250 - 120) / 50 = 2.6 U
        self.assertEqual(calculate_correction_dose(250, 120, 50.0), 2.6)

    def test_correction_at_target(self):
        self.assertEqual(calculate_correction_dose(120, 120, 50.0), 0.0)

    def test_correction_below_target(self):
        self.assertEqual(calculate_correction_dose(80, 120, 50.0), 0.0)

    def test_correction_high_glucose(self):
        # (400 - 100) / 30 = 10.0 U
        self.assertEqual(calculate_correction_dose(400, 100, 30.0), 10.0)

    def test_correction_zero_factor(self):
        self.assertEqual(calculate_correction_dose(250, 120, 0.0), 0.0)

    def test_correction_none_glucose(self):
        self.assertEqual(calculate_correction_dose(None, 120, 50.0), 0.0)


class TestCalculateTotalDose(unittest.TestCase):
    """Testes para o calculo de dose total (bolus + correcao)."""

    def test_total_with_food_and_correction(self):
        # Bolus: 60/10 = 6.0, Correcao: (200-120)/50 = 1.6, Total: 7.6
        result = calculate_total_dose(
            carbs_ingested=60.0,
            current_glucose=200,
            insulin_carb_ratio=10.0,
            correction_factor=50.0,
            target_glucose=120
        )
        self.assertEqual(result["bolus_alimentar"], 6.0)
        self.assertEqual(result["dose_correcao"], 1.6)
        self.assertEqual(result["dose_total"], 7.6)

    def test_total_only_food(self):
        # Glicemia no alvo, so bolus alimentar
        result = calculate_total_dose(
            carbs_ingested=40.0,
            current_glucose=110,
            insulin_carb_ratio=10.0,
            correction_factor=50.0,
            target_glucose=120
        )
        self.assertEqual(result["bolus_alimentar"], 4.0)
        self.assertEqual(result["dose_correcao"], 0.0)
        self.assertEqual(result["dose_total"], 4.0)

    def test_total_only_correction(self):
        # Sem comida, so correcao
        result = calculate_total_dose(
            carbs_ingested=0.0,
            current_glucose=250,
            insulin_carb_ratio=10.0,
            correction_factor=50.0,
            target_glucose=120
        )
        self.assertEqual(result["bolus_alimentar"], 0.0)
        self.assertEqual(result["dose_correcao"], 2.6)
        self.assertEqual(result["dose_total"], 2.6)

    def test_total_no_action_needed(self):
        # Sem comida, glicemia no alvo
        result = calculate_total_dose(
            carbs_ingested=0.0,
            current_glucose=100,
            insulin_carb_ratio=10.0,
            correction_factor=50.0,
            target_glucose=120
        )
        self.assertEqual(result["dose_total"], 0.0)

    def test_total_returns_all_params(self):
        result = calculate_total_dose(60.0, 200, 10.0, 50.0, 120)
        self.assertIn("bolus_alimentar", result)
        self.assertIn("dose_correcao", result)
        self.assertIn("dose_total", result)
        self.assertIn("carbs_ingested", result)
        self.assertIn("current_glucose", result)
        self.assertIn("target_glucose", result)
        self.assertIn("insulin_carb_ratio", result)
        self.assertIn("correction_factor", result)


if __name__ == '__main__':
    unittest.main()
