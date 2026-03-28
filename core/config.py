import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not all([TELEGRAM_TOKEN, SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY]):
    raise ValueError("Erro de Configuracao: Variaveis de ambiente obrigatorias ausentes.")
