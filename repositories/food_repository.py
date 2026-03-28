# repositories/food_repository.py
import logging
from typing import List, Dict, Any, Optional
from database.supabase_client import supabase_db


def search_food(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Busca alimentos na tabela food_reference (TACO) por nome parcial."""
    try:
        response = (
            supabase_db.table("food_reference")
            .select("id, food_name, portion_size, unit, carbs_per_portion")
            .ilike("food_name", f"%{query}%")
            .limit(limit)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        logging.error(f"Erro ao buscar alimento: {e}")
        return []


def get_food_by_id(food_id: int) -> Optional[Dict[str, Any]]:
    """Busca alimento por ID."""
    try:
        response = (
            supabase_db.table("food_reference")
            .select("id, food_name, portion_size, unit, carbs_per_portion")
            .eq("id", food_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logging.error(f"Erro ao buscar alimento por id: {e}")
        return None
