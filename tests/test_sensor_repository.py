# tests/test_sensor_repository.py
import unittest
from unittest.mock import MagicMock, patch


class TestSensorRepository(unittest.TestCase):
    """Testes para o repositorio de integracoes de sensor."""

    @patch('repositories.sensor_repository.supabase_db')
    @patch('repositories.sensor_repository.encrypt_value')
    def test_upsert_sensor_integration(self, mock_encrypt, mock_db):
        mock_encrypt.return_value = "encrypted_password"
        mock_db.table.return_value.upsert.return_value.execute.return_value = MagicMock(
            data=[{
                "telegram_user_id": 123,
                "llu_email": "test@email.com",
                "llu_password_hash": "encrypted_password",
                "llu_region_code": "BR",
                "status": "ACTIVE",
            }]
        )

        from repositories.sensor_repository import upsert_sensor_integration
        result = upsert_sensor_integration(123, "test@email.com", "senha123", "BR")

        self.assertEqual(result["telegram_user_id"], 123)
        mock_encrypt.assert_called_once_with("senha123")

    @patch('repositories.sensor_repository.supabase_db')
    @patch('repositories.sensor_repository.decrypt_value')
    def test_get_sensor_integration(self, mock_decrypt, mock_db):
        mock_decrypt.return_value = "senha_original"
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "telegram_user_id": 123,
                "llu_email": "test@email.com",
                "llu_password_hash": "encrypted",
                "llu_region_code": "BR",
                "status": "ACTIVE",
            }]
        )

        from repositories.sensor_repository import get_sensor_integration
        result = get_sensor_integration(123)

        self.assertIsNotNone(result)
        self.assertEqual(result["llu_password"], "senha_original")

    @patch('repositories.sensor_repository.supabase_db')
    @patch('repositories.sensor_repository.decrypt_value')
    def test_get_sensor_integration_not_found(self, mock_decrypt, mock_db):
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        from repositories.sensor_repository import get_sensor_integration
        result = get_sensor_integration(999)
        self.assertIsNone(result)

    @patch('repositories.sensor_repository.supabase_db')
    def test_update_sync_status(self, mock_db):
        from repositories.sensor_repository import update_sync_status
        update_sync_status(123, "2026-04-01T12:00:00Z", llu_patient_uuid="uuid-123")
        mock_db.table.return_value.update.assert_called_once()

    @patch('repositories.sensor_repository.supabase_db')
    def test_deactivate_sensor(self, mock_db):
        from repositories.sensor_repository import deactivate_sensor_integration
        deactivate_sensor_integration(123)
        mock_db.table.return_value.update.assert_called_once()


if __name__ == '__main__':
    unittest.main()
