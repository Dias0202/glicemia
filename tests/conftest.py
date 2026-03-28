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
