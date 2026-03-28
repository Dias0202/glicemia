# tests/test_food_repository.py
import unittest
from unittest.mock import patch, MagicMock


class TestSearchFood(unittest.TestCase):

    @patch('repositories.food_repository.supabase_db')
    def test_search_food_found(self, mock_db):
        from repositories.food_repository import search_food

        mock_response = MagicMock()
        mock_response.data = [
            {"id": 1, "food_name": "Arroz branco", "portion_size": 100.0, "unit": "g", "carbs_per_portion": 28.1},
        ]
        mock_db.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_response

        result = search_food("arroz")
        self.assertEqual(len(result), 1)
        self.assertIn("id", result[0])

    @patch('repositories.food_repository.supabase_db')
    def test_search_food_not_found(self, mock_db):
        from repositories.food_repository import search_food

        mock_response = MagicMock()
        mock_response.data = []
        mock_db.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_response

        result = search_food("xyz")
        self.assertEqual(result, [])

    @patch('repositories.food_repository.supabase_db')
    def test_search_food_error(self, mock_db):
        from repositories.food_repository import search_food
        mock_db.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.side_effect = Exception("err")
        self.assertEqual(search_food("arroz"), [])


class TestGetFoodById(unittest.TestCase):

    @patch('repositories.food_repository.supabase_db')
    def test_get_food_found(self, mock_db):
        from repositories.food_repository import get_food_by_id

        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "food_name": "Banana", "carbs_per_portion": 22.8}]
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response

        result = get_food_by_id(1)
        self.assertIsNotNone(result)
        self.assertEqual(result["food_name"], "Banana")

    @patch('repositories.food_repository.supabase_db')
    def test_get_food_not_found(self, mock_db):
        from repositories.food_repository import get_food_by_id

        mock_response = MagicMock()
        mock_response.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response

        result = get_food_by_id(999)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
