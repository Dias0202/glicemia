# core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not all([TELEGRAM_TOKEN, SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY]):
    raise ValueError("Erro de Configuracao: Variaveis de ambiente obrigatorias ausentes.")

# --- Configuracoes do CGM (LibreLinkUp) ---
CGM_SYNC_INTERVAL_MINUTES = int(os.getenv("CGM_SYNC_INTERVAL_MINUTES", "5"))
CGM_ENABLED = os.getenv("CGM_ENABLED", "false").lower() == "true"

# --- Limiares clinicos ---
HYPO_THRESHOLD = int(os.getenv("HYPO_THRESHOLD", "70"))
HYPER_THRESHOLD = int(os.getenv("HYPER_THRESHOLD", "180"))
SEVERE_HYPER_THRESHOLD = int(os.getenv("SEVERE_HYPER_THRESHOLD", "250"))
URGENT_LOW_THRESHOLD = int(os.getenv("URGENT_LOW_THRESHOLD", "54"))
