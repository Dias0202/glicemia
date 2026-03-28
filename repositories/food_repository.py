# repositories/food_repository.py
import logging
from typing import List, Dict, Any, Optional
from database.supabase_client import supabase_db


def search_food(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Busca alimentos na tabela food_reference (TACO) por nome parcial (ilike).
    Retorna os resultados mais relevantes.
    """
    try:
        response = (
            supabase_db.table("food_reference")
            .select("food_name, portion_size, unit, carbs_per_portion")
            .ilike("food_name", f"%{query}%")
            .limit(limit)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        logging.error(f"Erro ao buscar alimento: {e}")
        return []


def get_food_by_name(food_name: str) -> Optional[Dict[str, Any]]:
    """
    Busca um alimento exato na tabela food_reference.
    """
    try:
        response = (
            supabase_db.table("food_reference")
            .select("food_name, portion_size, unit, carbs_per_portion")
            .ilike("food_name", food_name)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logging.error(f"Erro ao buscar alimento por nome: {e}")
        return None
