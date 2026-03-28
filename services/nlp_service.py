# services/nlp_service.py
import json
import logging
from groq import Groq
from core.config import GROQ_API_KEY

# Inicializa o cliente do Groq
client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """
Você é um sistema especializado em extração de dados médicos estruturados.
O usuário enviará um texto natural descrevendo seu estado atual, refeição, glicemia e insulina.
Extraia as informações e retorne EXCLUSIVAMENTE um objeto JSON válido, sem nenhum texto adicional.

Regras de Extração e Tipos de Dados:
- "glucose_level": inteiro ou null (nível de glicose aferido).
- "carbs_ingested": numérico ou null (estimativa de carboidratos consumidos).
- "bolus_insulin": numérico ou null (insulina rápida/ultrarrápida aplicada).
- "basal_insulin": numérico ou null (insulina lenta/basal aplicada).
- "exercise_done": booleano (true se o usuário mencionar que treinou/fez exercício, false caso contrário).
- "exercise_intensity": string ou null (valores exatos permitidos: "Baixa", "Média", "Alta").
- "mood": string ou null (estado emocional inferido do texto).
- "refeicao": string (ex: "Café da manhã", "Almoço", "Jantar", "Lanche", "Correção"). Se não houver contexto, use "Não especificada".

Exemplo de entrada: "Minha glicemia ta 120, vou almoçar, uns 50g de carbo. Tomei 5 de rapida. Treinei perna forte hj."
Exemplo de saída JSON:
{
  "glucose_level": 120,
  "carbs_ingested": 50.0,
  "bolus_insulin": 5.0,
  "basal_insulin": null,
  "exercise_done": true,
  "exercise_intensity": "Alta",
  "mood": null,
  "refeicao": "Almoço"
}
"""

def extract_health_data(user_text: str) -> dict:
    """
    Processa a entrada de texto do usuário via API do Groq e retorna um dicionário extraído.
    """
    response_content = None
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_text,
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        response_content = chat_completion.choices[0].message.content
        return json.loads(response_content)

    except json.JSONDecodeError as e:
        logging.error(f"Falha ao decodificar JSON retornado pelo Groq: {e} - Resposta: {response_content}")
        raise ValueError("Erro de formatação na resposta da IA.")
    except Exception as e:
        logging.error(f"Erro na comunicação com a API do Groq: {e}")
        raise e