# services/voice_service.py
import logging
from groq import Groq
from core.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)


async def transcribe_voice(voice_file_bytes: bytearray) -> str:
    """
    Transcreve audio de voz para texto usando Groq Whisper API.
    Recebe os bytes do arquivo de audio (OGG do Telegram) e retorna o texto transcrito.
    """
    try:
        transcription = client.audio.transcriptions.create(
            file=("audio.ogg", bytes(voice_file_bytes)),
            model="whisper-large-v3-turbo",
            language="pt",
            response_format="text",
        )
        text = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
        logging.info(f"Transcricao de voz: {text}")
        return text
    except Exception as e:
        logging.error(f"Erro na transcricao de voz: {e}")
        raise e
