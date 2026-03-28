# repositories/meal_repository.py
import json
import logging
from typing import List, Dict, Any, Optional
from database.supabase_client import supabase_db


def save_meal(
    telegram_user_id: int,
    meal_name: str,
    items: List[Dict[str, Any]],
    total_carbs: float
) -> Dict[str, Any]:
    """
    Salva uma refeicao favorita do usuario.
    items: [{"food_name": "Arroz", "quantity_g": 200, "carbs": 56.2}, ...]
    """
    data = {
        "telegram_user_id": telegram_user_id,
        "meal_name": meal_name,
        "items": json.dumps(items, ensure_ascii=False),
        "total_carbs": total_carbs,
    }
    try:
        response = supabase_db.table("saved_meals").insert(data).execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        logging.error(f"Erro ao salvar refeicao: {e}")
        raise e


def get_saved_meals(telegram_user_id: int) -> List[Dict[str, Any]]:
    """Retorna as refeicoes salvas do usuario."""
    try:
        response = (
            supabase_db.table("saved_meals")
            .select("id, meal_name, items, total_carbs")
            .eq("telegram_user_id", telegram_user_id)
            .order("meal_name")
            .execute()
        )
        results = response.data if response.data else []
        for r in results:
            if isinstance(r.get("items"), str):
                r["items"] = json.loads(r["items"])
        return results
    except Exception as e:
        logging.error(f"Erro ao buscar refeicoes salvas: {e}")
        return []


def delete_saved_meal(meal_id: int, telegram_user_id: int) -> bool:
    """Remove uma refeicao salva."""
    try:
        supabase_db.table("saved_meals").delete().eq(
            "id", meal_id
        ).eq(
            "telegram_user_id", telegram_user_id
        ).execute()
        return True
    except Exception as e:
        logging.error(f"Erro ao deletar refeicao: {e}")
        return False
