# tests/test_calculator_service.py
import unittest
from services.calculator_service import (
    calculate_carb_bolus,
    calculate_correction_dose,
    calculate_total_dose,
    EXERCISE_FACTORS,
)


class TestCalculateCarbBolus(unittest.TestCase):

    def test_bolus_normal(self):
        self.assertEqual(calculate_carb_bolus(60.0, 10.0), 6.0)

    def test_bolus_icr_15(self):
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
        self.assertEqual(calculate_carb_bolus(33.0, 10.0), 3.3)


class TestCalculateCorrectionDose(unittest.TestCase):

    def test_correction_above_target(self):
        self.assertEqual(calculate_correction_dose(250, 120, 50.0), 2.6)

    def test_correction_at_target(self):
        self.assertEqual(calculate_correction_dose(120, 120, 50.0), 0.0)

    def test_correction_below_target(self):
        self.assertEqual(calculate_correction_dose(80, 120, 50.0), 0.0)

    def test_correction_zero_factor(self):
        self.assertEqual(calculate_correction_dose(250, 120, 0.0), 0.0)

    def test_correction_none_glucose(self):
        self.assertEqual(calculate_correction_dose(None, 120, 50.0), 0.0)


class TestCalculateTotalDose(unittest.TestCase):

    def test_total_with_food_and_correction(self):
        result = calculate_total_dose(60.0, 200, 10.0, 50.0, 120)
        self.assertEqual(result["bolus_alimentar"], 6.0)
        self.assertEqual(result["dose_correcao"], 1.6)
        self.assertEqual(result["dose_total"], 7.6)

    def test_total_only_food(self):
        result = calculate_total_dose(40.0, 110, 10.0, 50.0, 120)
        self.assertEqual(result["dose_total"], 4.0)

    def test_total_only_correction(self):
        result = calculate_total_dose(0.0, 250, 10.0, 50.0, 120)
        self.assertEqual(result["dose_total"], 2.6)

    def test_total_no_action(self):
        result = calculate_total_dose(0.0, 100, 10.0, 50.0, 120)
        self.assertEqual(result["dose_total"], 0.0)

    def test_exercise_leve(self):
        result = calculate_total_dose(60.0, 200, 10.0, 50.0, 120, "leve")
        # Subtotal = 7.6, leve = 0.90, total = 6.84
        self.assertEqual(result["subtotal"], 7.6)
        self.assertEqual(result["dose_total"], 6.84)
        self.assertGreater(result["exercise_reduction"], 0)

    def test_exercise_moderado(self):
        result = calculate_total_dose(60.0, 200, 10.0, 50.0, 120, "moderado")
        # Subtotal = 7.6, moderado = 0.80, total = 6.08
        self.assertEqual(result["dose_total"], 6.08)

    def test_exercise_intenso(self):
        result = calculate_total_dose(60.0, 200, 10.0, 50.0, 120, "intenso")
        # Subtotal = 7.6, intenso = 0.70, total = 5.32
        self.assertEqual(result["dose_total"], 5.32)

    def test_exercise_nenhum(self):
        result = calculate_total_dose(60.0, 200, 10.0, 50.0, 120, "nenhum")
        self.assertEqual(result["dose_total"], 7.6)
        self.assertEqual(result["exercise_reduction"], 0)


class TestExerciseFactors(unittest.TestCase):

    def test_factors_exist(self):
        self.assertIn("nenhum", EXERCISE_FACTORS)
        self.assertIn("leve", EXERCISE_FACTORS)
        self.assertIn("moderado", EXERCISE_FACTORS)
        self.assertIn("intenso", EXERCISE_FACTORS)

    def test_nenhum_is_1(self):
        self.assertEqual(EXERCISE_FACTORS["nenhum"], 1.0)

    def test_factors_decrease(self):
        self.assertGreater(EXERCISE_FACTORS["leve"], EXERCISE_FACTORS["moderado"])
        self.assertGreater(EXERCISE_FACTORS["moderado"], EXERCISE_FACTORS["intenso"])


if __name__ == '__main__':
    unittest.main()
