# tests/test_food_repository.py
import unittest
from unittest.mock import patch, MagicMock


class TestSearchFood(unittest.TestCase):
    """Testes para a busca de alimentos na tabela TACO."""

    @patch('repositories.food_repository.supabase_db')
    def test_search_food_found(self, mock_db):
        from repositories.food_repository import search_food

        mock_response = MagicMock()
        mock_response.data = [
            {"food_name": "Arroz branco", "portion_size": 100.0, "unit": "g", "carbs_per_portion": 28.1},
            {"food_name": "Arroz integral", "portion_size": 100.0, "unit": "g", "carbs_per_portion": 25.8},
        ]
        mock_db.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_response

        result = search_food("arroz")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["food_name"], "Arroz branco")

    @patch('repositories.food_repository.supabase_db')
    def test_search_food_not_found(self, mock_db):
        from repositories.food_repository import search_food

        mock_response = MagicMock()
        mock_response.data = []
        mock_db.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_response

        result = search_food("xyzinexistente")
        self.assertEqual(result, [])

    @patch('repositories.food_repository.supabase_db')
    def test_search_food_error(self, mock_db):
        from repositories.food_repository import search_food

        mock_db.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.side_effect = Exception("DB Error")

        result = search_food("arroz")
        self.assertEqual(result, [])


class TestGetFoodByName(unittest.TestCase):
    """Testes para busca exata de alimento."""

    @patch('repositories.food_repository.supabase_db')
    def test_get_food_found(self, mock_db):
        from repositories.food_repository import get_food_by_name

        mock_response = MagicMock()
        mock_response.data = [
            {"food_name": "Banana", "portion_size": 100.0, "unit": "g", "carbs_per_portion": 22.8},
        ]
        mock_db.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_response

        result = get_food_by_name("Banana")
        self.assertIsNotNone(result)
        self.assertEqual(result["carbs_per_portion"], 22.8)

    @patch('repositories.food_repository.supabase_db')
    def test_get_food_not_found(self, mock_db):
        from repositories.food_repository import get_food_by_name

        mock_response = MagicMock()
        mock_response.data = []
        mock_db.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_response

        result = get_food_by_name("AlimentoInexistente")
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
