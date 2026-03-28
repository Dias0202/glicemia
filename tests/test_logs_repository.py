# tests/test_logs_repository.py
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestInsertGlycemicLog(unittest.TestCase):
    """Testes para a insercao de logs glicemicos (com mock do Supabase)."""

    @patch('repositories.logs_repository.supabase_db')
    def test_insert_log_basic(self, mock_db):
        from repositories.logs_repository import insert_glycemic_log

        mock_response = MagicMock()
        mock_response.data = [{"id": 1, "glucose_level": 120}]
        mock_db.table.return_value.insert.return_value.execute.return_value = mock_response

        result = insert_glycemic_log(
            telegram_user_id=12345,
            glucose_level=120,
            carbs_ingested=30.0,
            bolus_insulin=3.0,
            refeicao="Almoco"
        )

        mock_db.table.assert_called_with("glycemic_logs")
        self.assertEqual(result["glucose_level"], 120)

    @patch('repositories.logs_repository.supabase_db')
    def test_insert_log_with_timestamp(self, mock_db):
        from repositories.logs_repository import insert_glycemic_log

        mock_response = MagicMock()
        mock_response.data = [{"id": 2}]
        mock_db.table.return_value.insert.return_value.execute.return_value = mock_response

        result = insert_glycemic_log(
            telegram_user_id=12345,
            glucose_level=90,
            timestamp="2026-03-20T10:00:00+00:00"
        )

        call_args = mock_db.table.return_value.insert.call_args[0][0]
        self.assertEqual(call_args["timestamp"], "2026-03-20T10:00:00+00:00")

    @patch('repositories.logs_repository.supabase_db')
    def test_insert_log_none_values_excluded(self, mock_db):
        from repositories.logs_repository import insert_glycemic_log

        mock_response = MagicMock()
        mock_response.data = [{"id": 3}]
        mock_db.table.return_value.insert.return_value.execute.return_value = mock_response

        insert_glycemic_log(telegram_user_id=12345, glucose_level=100)

        call_args = mock_db.table.return_value.insert.call_args[0][0]
        self.assertNotIn("carbs_ingested", call_args)
        self.assertNotIn("bolus_insulin", call_args)
        self.assertIn("telegram_user_id", call_args)

    @patch('repositories.logs_repository.supabase_db')
    def test_insert_log_auto_timestamp(self, mock_db):
        from repositories.logs_repository import insert_glycemic_log

        mock_response = MagicMock()
        mock_response.data = [{"id": 4}]
        mock_db.table.return_value.insert.return_value.execute.return_value = mock_response

        insert_glycemic_log(telegram_user_id=12345, glucose_level=110)

        call_args = mock_db.table.return_value.insert.call_args[0][0]
        self.assertIn("timestamp", call_args)
        # Verifica que o timestamp e ISO 8601
        self.assertIn("T", call_args["timestamp"])


class TestGetRecentLogs(unittest.TestCase):
    """Testes para a consulta de logs recentes."""

    @patch('repositories.logs_repository.supabase_db')
    def test_get_recent_logs(self, mock_db):
        from repositories.logs_repository import get_recent_logs

        mock_response = MagicMock()
        mock_response.data = [
            {"glucose_level": 120, "timestamp": "2026-03-20T08:00:00"},
            {"glucose_level": 90, "timestamp": "2026-03-20T12:00:00"},
        ]
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        result = get_recent_logs(12345, limit=10)
        self.assertEqual(len(result), 2)

    @patch('repositories.logs_repository.supabase_db')
    def test_get_recent_logs_empty(self, mock_db):
        from repositories.logs_repository import get_recent_logs

        mock_response = MagicMock()
        mock_response.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        result = get_recent_logs(12345)
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
