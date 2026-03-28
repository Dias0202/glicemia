# tests/test_meal_repository.py
import unittest
from unittest.mock import patch, MagicMock
import json


class TestSaveMeal(unittest.TestCase):

    @patch('repositories.meal_repository.supabase_db')
    def test_save_meal(self, mock_db):
        from repositories.meal_repository import save_meal

        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "meal_name": "Almoco"}]
        mock_db.table.return_value.insert.return_value.execute.return_value = mock_response

        items = [{"food_name": "Arroz", "quantity_g": 200, "carbs": 56.2}]
        result = save_meal(12345, "Almoco", items, 56.2)

        self.assertEqual(result["meal_name"], "Almoco")
        call_args = mock_db.table.return_value.insert.call_args[0][0]
        self.assertEqual(call_args["meal_name"], "Almoco")
        self.assertEqual(call_args["total_carbs"], 56.2)


class TestGetSavedMeals(unittest.TestCase):

    @patch('repositories.meal_repository.supabase_db')
    def test_get_saved_meals(self, mock_db):
        from repositories.meal_repository import get_saved_meals

        mock_response = MagicMock()
        mock_response.data = [
            {"id": 1, "meal_name": "Almoco", "items": json.dumps([{"food_name": "Arroz"}]), "total_carbs": 56.2},
        ]
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        result = get_saved_meals(12345)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0]["items"], list)

    @patch('repositories.meal_repository.supabase_db')
    def test_get_saved_meals_empty(self, mock_db):
        from repositories.meal_repository import get_saved_meals

        mock_response = MagicMock()
        mock_response.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        result = get_saved_meals(12345)
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
