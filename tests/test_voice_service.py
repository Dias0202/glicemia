# tests/test_voice_service.py
import unittest
from unittest.mock import patch, MagicMock
import asyncio


class TestTranscribeVoice(unittest.TestCase):
    """Testes para o servico de transcricao de voz."""

    @patch('services.voice_service.client')
    def test_transcribe_success(self, mock_client):
        from services.voice_service import transcribe_voice

        mock_client.audio.transcriptions.create.return_value = "cento e vinte"

        result = asyncio.run(transcribe_voice(bytearray(b"fake_audio_bytes")))
        self.assertEqual(result, "cento e vinte")

        mock_client.audio.transcriptions.create.assert_called_once()
        call_kwargs = mock_client.audio.transcriptions.create.call_args[1]
        self.assertEqual(call_kwargs["model"], "whisper-large-v3-turbo")
        self.assertEqual(call_kwargs["language"], "pt")

    @patch('services.voice_service.client')
    def test_transcribe_returns_object(self, mock_client):
        from services.voice_service import transcribe_voice

        mock_response = MagicMock()
        mock_response.text = "  duzentos mg  "
        mock_client.audio.transcriptions.create.return_value = mock_response

        result = asyncio.run(transcribe_voice(bytearray(b"audio")))
        self.assertEqual(result, "duzentos mg")

    @patch('services.voice_service.client')
    def test_transcribe_error(self, mock_client):
        from services.voice_service import transcribe_voice

        mock_client.audio.transcriptions.create.side_effect = Exception("API Error")

        with self.assertRaises(Exception):
            asyncio.run(transcribe_voice(bytearray(b"audio")))


if __name__ == '__main__':
    unittest.main()
