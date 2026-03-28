# services/portion_service.py
import re
import logging

# Tabela de conversao de medidas caseiras para gramas.
# Valores medios baseados em tabelas de medidas caseiras brasileiras.
MEASURES = {
    "colher de sopa": 25,
    "colheres de sopa": 25,
    "cs": 25,
    "colher de cha": 5,
    "colheres de cha": 5,
    "cc": 5,
    "colher de sobremesa": 15,
    "colheres de sobremesa": 15,
    "xicara": 160,
    "xicaras": 160,
    "xic": 160,
    "concha": 100,
    "conchas": 100,
    "unidade": 80,
    "unidades": 80,
    "un": 80,
    "fatia": 30,
    "fatias": 30,
    "pedaco": 50,
    "pedacos": 50,
    "copo": 240,
    "copos": 240,
    "prato": 300,
    "pratos": 300,
    "escumadeira": 80,
    "pegador": 45,
    "pegadores": 45,
}

# Ordenar por tamanho da chave (maior primeiro) para match correto
_SORTED_MEASURES = sorted(MEASURES.keys(), key=len, reverse=True)


def parse_quantity(text: str) -> float:
    """
    Converte uma entrada de quantidade do usuario em gramas.

    Aceita:
      - "200g" ou "200 g" ou "200 gramas" ou "200" -> 200g
      - "2 colheres de sopa" -> 50g
      - "1 xicara" -> 160g
      - "3 fatias" -> 90g
      - "meia colher de sopa" -> 12.5g
      - Se nao entender, retorna 100g (porcao padrao TACO)
    """
    text = text.lower().strip()

    # Tratar "meia" e "meio" como 0.5
    text = re.sub(r'\bmeio\b|\bmeia\b', '0.5', text)

    # Extrair numero do inicio
    num_match = re.match(r'(\d+[.,]?\d*)', text)
    quantity = float(num_match.group(1).replace(',', '.')) if num_match else 1.0

    # Verificar se e gramas (ex: "200g", "200 gramas", "200 g")
    if re.search(r'g(ramas?)?\b', text):
        return quantity

    # Verificar medidas caseiras
    for measure in _SORTED_MEASURES:
        if measure in text:
            return round(quantity * MEASURES[measure], 1)

    # Se so digitou um numero, assume gramas
    if num_match and len(text.strip()) == len(num_match.group(0)):
        return quantity

    # Fallback: 100g (porcao padrao TACO)
    return 100.0


def calculate_carbs_from_portion(carbs_per_100g: float, quantity_grams: float) -> float:
    """Calcula carboidratos baseado na porcao em gramas."""
    if carbs_per_100g <= 0 or quantity_grams <= 0:
        return 0.0
    return round((quantity_grams / 100.0) * carbs_per_100g, 1)


def format_portion_help() -> str:
    """Retorna texto de ajuda sobre medidas aceitas."""
    return (
        "Formatos aceitos:\n"
        "  200g ou 200 gramas\n"
        "  2 colheres de sopa\n"
        "  1 xicara\n"
        "  1 concha\n"
        "  3 fatias\n"
        "  1 unidade\n"
        "  1 copo\n"
        "  1 prato\n"
        "  meia colher de sopa"
    )
