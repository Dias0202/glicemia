from supabase import create_client, Client
from core.config import SUPABASE_URL, SUPABASE_KEY

def get_supabase_client() -> Client:
    """
    Inicializa e retorna o cliente do Supabase.
    """
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase
    except Exception as e:
        raise ConnectionError(f"Falha ao conectar com o Supabase: {str(e)}")

# Instância global a ser importada pelos repositórios
supabase_db = get_supabase_client()