# tests/test_user_repository.py
import sys
import unittest
from unittest.mock import MagicMock

# Mock do modulo supabase antes de importar o repositorio
sys.modules['supabase'] = MagicMock()
sys.modules['database.supabase_client'] = MagicMock()

from repositories.user_repository import calculate_bmi


class TestCalculateBMI(unittest.TestCase):
    """Testes para o calculo de IMC."""

    def test_bmi_normal(self):
        # Peso: 70kg, Altura: 1.75m -> IMC = 70 / (1.75^2) = 22.86
        self.assertEqual(calculate_bmi(70.0, 1.75), 22.86)

    def test_bmi_height_in_cm(self):
        # Altura em centimetros (175) deve ser convertida para metros
        result = calculate_bmi(70.0, 175.0)
        self.assertEqual(result, 22.86)

    def test_bmi_height_zero(self):
        self.assertEqual(calculate_bmi(70.0, 0.0), 0.0)

    def test_bmi_height_negative(self):
        self.assertEqual(calculate_bmi(70.0, -1.0), 0.0)

    def test_bmi_obese(self):
        # Peso: 120kg, Altura: 1.70m -> IMC = 120 / (1.70^2) = 41.52
        self.assertEqual(calculate_bmi(120.0, 1.70), 41.52)

    def test_bmi_underweight(self):
        # Peso: 45kg, Altura: 1.70m -> IMC = 45 / (1.70^2) = 15.57
        self.assertEqual(calculate_bmi(45.0, 1.70), 15.57)


if __name__ == '__main__':
    unittest.main()
