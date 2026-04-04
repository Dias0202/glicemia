# tests/conftest.py
import sys
from unittest.mock import MagicMock

# Mock de modulos externos que requerem credenciais/conexao
# Isso permite rodar testes unitarios sem .env ou conexao com Supabase/Groq
if 'supabase' not in sys.modules:
    sys.modules['supabase'] = MagicMock()

mock_supabase_client = MagicMock()
mock_supabase_client.supabase_db = MagicMock()
sys.modules['database.supabase_client'] = mock_supabase_client

mock_groq = MagicMock()
sys.modules['groq'] = mock_groq

# Mock pylibrelinkup para testes sem a biblioteca real
mock_pylibrelinkup = MagicMock()
sys.modules['pylibrelinkup'] = mock_pylibrelinkup

# Mock core.config para testes
mock_config = MagicMock()
mock_config.TELEGRAM_TOKEN = "test_token"
mock_config.SUPABASE_URL = "https://test.supabase.co"
mock_config.SUPABASE_KEY = "test_key_12345678901234567890123456789012"
mock_config.GROQ_API_KEY = "test_groq_key"
mock_config.CGM_SYNC_INTERVAL_MINUTES = 5
mock_config.CGM_ENABLED = False
mock_config.HYPO_THRESHOLD = 70
mock_config.HYPER_THRESHOLD = 180
mock_config.SEVERE_HYPER_THRESHOLD = 250
mock_config.URGENT_LOW_THRESHOLD = 54
sys.modules['core.config'] = mock_config
