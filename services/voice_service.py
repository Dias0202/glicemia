# services/voice_service.py
"""
Transcricao de audio via Groq Whisper API.
Suporta mensagens de voz e audio do Telegram.
"""
import logging
import tempfile
import os
from typing import Optional
from groq import Groq
from core.config import GROQ_API_KEY

WHISPER_MODEL = "whisper-large-v3-turbo"


def transcribe_audio(file_path: str) -> Optional[str]:
    """
    Transcreve um arquivo de audio usando Groq Whisper.
    Retorna o texto transcrito ou None em caso de erro.
    """
    try:
        client = Groq(api_key=GROQ_API_KEY)
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=audio_file,
                language="pt",
                response_format="text",
            )
        text = transcription.strip() if isinstance(transcription, str) else str(transcription).strip()
        if text:
            logging.info(f"Transcricao: '{text[:80]}...'")
            return text
        return None
    except Exception as e:
        logging.error(f"Erro transcricao Whisper: {e}")
        return None


async def transcribe_telegram_voice(voice_or_audio, context) -> Optional[str]:
    """
    Baixa arquivo de voz/audio do Telegram e transcreve.
    Aceita tanto voice quanto audio message.
    """
    tmp_path = None
    try:
        file = await context.bot.get_file(voice_or_audio.file_id)
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".ogg")
        os.close(tmp_fd)
        await file.download_to_drive(tmp_path)
        return transcribe_audio(tmp_path)
    except Exception as e:
        logging.error(f"Erro ao processar audio Telegram: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
