import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente local
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Fator de sensibilidade/carboidrato. Default = 15.0 se não for encontrado.
CARB_FACTOR = float(os.getenv("CARB_FACTOR", 15.0))

# Validação estrita para garantir que a aplicação não inicie sem as chaves vitais
if not all([TELEGRAM_TOKEN, SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY]):
    raise ValueError("Erro de Configuração: Variáveis de ambiente obrigatórias ausentes.")