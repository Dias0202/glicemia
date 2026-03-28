# tests/test_calculator_service.py
import unittest
from unittest.mock import patch


class TestCalculateBolus(unittest.TestCase):
    """Testes para o calculo de dose de insulina bolus."""

    @patch('services.calculator_service.CARB_FACTOR', 10.0)
    def test_bolus_normal(self):
        from services.calculator_service import calculate_bolus
        self.assertEqual(calculate_bolus(50.0), 5.0)

    @patch('services.calculator_service.CARB_FACTOR', 15.0)
    def test_bolus_fator_15(self):
        from services.calculator_service import calculate_bolus
        self.assertEqual(calculate_bolus(45.0), 3.0)

    @patch('services.calculator_service.CARB_FACTOR', 10.0)
    def test_bolus_zero_carbs(self):
        from services.calculator_service import calculate_bolus
        self.assertEqual(calculate_bolus(0.0), 0.0)

    @patch('services.calculator_service.CARB_FACTOR', 10.0)
    def test_bolus_negative_carbs(self):
        from services.calculator_service import calculate_bolus
        self.assertEqual(calculate_bolus(-5.0), 0.0)

    @patch('services.calculator_service.CARB_FACTOR', 10.0)
    def test_bolus_none_carbs(self):
        from services.calculator_service import calculate_bolus
        self.assertEqual(calculate_bolus(None), 0.0)

    @patch('services.calculator_service.CARB_FACTOR', 10.0)
    def test_bolus_rounding(self):
        from services.calculator_service import calculate_bolus
        result = calculate_bolus(33.0)
        self.assertEqual(result, 3.3)


if __name__ == '__main__':
    unittest.main()
