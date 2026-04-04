# core/security.py
"""
Modulo de seguranca para criptografia de credenciais sensiveis.
Usa Fernet (AES-128-CBC) para criptografar senhas do LibreLinkUp.
A chave de criptografia e derivada do SUPABASE_KEY via PBKDF2.
"""
import base64
import hashlib
import logging
from cryptography.fernet import Fernet, InvalidToken

_fernet_instance = None


def _get_fernet() -> Fernet:
    """Retorna instancia Fernet derivada do SUPABASE_KEY como seed."""
    global _fernet_instance
    if _fernet_instance is None:
        from core.config import SUPABASE_KEY
        key = hashlib.pbkdf2_hmac(
            'sha256',
            SUPABASE_KEY.encode(),
            b'glycemibot_salt_v1',
            100_000,
        )
        fernet_key = base64.urlsafe_b64encode(key[:32])
        _fernet_instance = Fernet(fernet_key)
    return _fernet_instance


def encrypt_value(plaintext: str) -> str:
    """Criptografa um valor e retorna string base64."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Descriptografa um valor criptografado."""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logging.error("Falha ao descriptografar: token invalido")
        raise ValueError("Credencial corrompida ou chave alterada")
