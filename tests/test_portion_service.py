# tests/test_portion_service.py
import unittest
from services.portion_service import parse_quantity, calculate_carbs_from_portion


class TestParseQuantity(unittest.TestCase):
    """Testes para conversao de medidas caseiras em gramas."""

    def test_gramas_numero(self):
        self.assertEqual(parse_quantity("200g"), 200.0)

    def test_gramas_com_espaco(self):
        self.assertEqual(parse_quantity("200 g"), 200.0)

    def test_gramas_palavra(self):
        self.assertEqual(parse_quantity("200 gramas"), 200.0)

    def test_so_numero(self):
        self.assertEqual(parse_quantity("150"), 150.0)

    def test_colher_de_sopa(self):
        self.assertEqual(parse_quantity("2 colheres de sopa"), 50.0)

    def test_colher_de_cha(self):
        self.assertEqual(parse_quantity("3 colheres de cha"), 15.0)

    def test_xicara(self):
        self.assertEqual(parse_quantity("1 xicara"), 160.0)

    def test_concha(self):
        self.assertEqual(parse_quantity("2 conchas"), 200.0)

    def test_fatia(self):
        self.assertEqual(parse_quantity("3 fatias"), 90.0)

    def test_unidade(self):
        self.assertEqual(parse_quantity("1 unidade"), 80.0)

    def test_copo(self):
        self.assertEqual(parse_quantity("1 copo"), 240.0)

    def test_prato(self):
        self.assertEqual(parse_quantity("1 prato"), 300.0)

    def test_meia_colher(self):
        self.assertEqual(parse_quantity("meia colher de sopa"), 12.5)

    def test_virgula_decimal(self):
        self.assertEqual(parse_quantity("1,5 colheres de sopa"), 37.5)

    def test_fallback_sem_unidade(self):
        # Texto sem numero e sem unidade -> 100g
        self.assertEqual(parse_quantity("um pouco"), 100.0)

    def test_abreviacao_cs(self):
        self.assertEqual(parse_quantity("2 cs"), 50.0)


class TestCalculateCarbsFromPortion(unittest.TestCase):
    """Testes para calculo de carbs baseado em porcao."""

    def test_normal(self):
        # Arroz: 28.1g carbs/100g, porcao de 200g -> 56.2g carbs
        self.assertEqual(calculate_carbs_from_portion(28.1, 200.0), 56.2)

    def test_metade(self):
        # 50g de algo com 20g carbs/100g -> 10g carbs
        self.assertEqual(calculate_carbs_from_portion(20.0, 50.0), 10.0)

    def test_zero_carbs(self):
        self.assertEqual(calculate_carbs_from_portion(0.0, 200.0), 0.0)

    def test_zero_quantity(self):
        self.assertEqual(calculate_carbs_from_portion(28.0, 0.0), 0.0)


if __name__ == '__main__':
    unittest.main()
