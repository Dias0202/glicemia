# services/vision_service.py
"""
Identificacao de alimentos via foto usando LLM multimodal (Groq).
O usuario tira uma foto do prato e o modelo identifica os alimentos
e estima porcoes, cruzando com a tabela TACO.
"""
import base64
import json
import logging
import tempfile
import os
from typing import Dict, Any, List, Optional
from groq import Groq
from core.config import GROQ_API_KEY
from repositories.food_repository import search_food

VISION_MODEL = "llama-3.2-90b-vision-preview"

FOOD_IDENTIFICATION_PROMPT = """Voce e um nutricionista especialista em alimentos brasileiros.
Analise a foto e identifique TODOS os alimentos visiveis no prato.

Para cada alimento, estime:
1. Nome do alimento em portugues (como apareceria na tabela TACO)
2. Quantidade estimada em gramas

Responda APENAS em JSON valido, sem markdown:
{"alimentos": [{"nome": "arroz branco", "gramas": 200}, {"nome": "feijao", "gramas": 150}]}

Se nao conseguir identificar alimentos, responda:
{"alimentos": [], "erro": "descricao do problema"}
"""


def identify_food_from_photo(image_path: str) -> Dict[str, Any]:
    """
    Analisa foto de refeicao e identifica alimentos com estimativa de porcao.
    Retorna dict com lista de alimentos identificados e match com TACO.
    """
    try:
        with open(image_path, "rb") as img_file:
            image_data = base64.b64encode(img_file.read()).decode("utf-8")

        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/jpeg")

        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": FOOD_IDENTIFICATION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}",
                            },
                        },
                    ],
                }
            ],
            max_tokens=1024,
            temperature=0.1,
        )

        content = response.choices[0].message.content.strip()
        # Limpar possivel markdown
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)

        if "erro" in result:
            return {"success": False, "error": result["erro"], "items": []}

        # Cruzar com TACO
        matched_items = []
        for item in result.get("alimentos", []):
            nome = item.get("nome", "")
            gramas = item.get("gramas", 100)
            taco_results = search_food(nome, limit=1)
            if taco_results:
                taco = taco_results[0]
                carbs = round((gramas / 100) * taco["carbs_per_portion"], 1)
                matched_items.append({
                    "food_name": taco["food_name"],
                    "food_id": taco["id"],
                    "quantity_g": gramas,
                    "carbs_per_100g": taco["carbs_per_portion"],
                    "carbs": carbs,
                    "matched_taco": True,
                })
            else:
                matched_items.append({
                    "food_name": nome,
                    "food_id": None,
                    "quantity_g": gramas,
                    "carbs_per_100g": None,
                    "carbs": None,
                    "matched_taco": False,
                })

        return {"success": True, "items": matched_items}

    except json.JSONDecodeError as e:
        logging.error(f"Erro ao parsear resposta de visao: {e}")
        return {"success": False, "error": "Nao foi possivel interpretar a imagem", "items": []}
    except Exception as e:
        logging.error(f"Erro no servico de visao: {e}")
        return {"success": False, "error": str(e), "items": []}


async def process_telegram_photo(photo, context) -> Dict[str, Any]:
    """Baixa foto do Telegram e identifica alimentos."""
    tmp_path = None
    try:
        file = await context.bot.get_file(photo.file_id)
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
        os.close(tmp_fd)
        await file.download_to_drive(tmp_path)
        return identify_food_from_photo(tmp_path)
    except Exception as e:
        logging.error(f"Erro ao processar foto Telegram: {e}")
        return {"success": False, "error": str(e), "items": []}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
