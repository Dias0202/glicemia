# tests/test_security.py
import unittest
from core.security import encrypt_value, decrypt_value


class TestEncryptDecrypt(unittest.TestCase):
    """Testes para criptografia de credenciais."""

    def test_encrypt_decrypt_roundtrip(self):
        original = "minha_senha_secreta_123!"
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        self.assertEqual(decrypted, original)

    def test_encrypted_differs_from_original(self):
        original = "senha_test"
        encrypted = encrypt_value(original)
        self.assertNotEqual(encrypted, original)

    def test_different_inputs_different_outputs(self):
        enc1 = encrypt_value("senha1")
        enc2 = encrypt_value("senha2")
        self.assertNotEqual(enc1, enc2)

    def test_empty_string(self):
        encrypted = encrypt_value("")
        decrypted = decrypt_value(encrypted)
        self.assertEqual(decrypted, "")

    def test_unicode_characters(self):
        original = "senhã_çöm_àcentos_日本語"
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        self.assertEqual(decrypted, original)

    def test_long_string(self):
        original = "a" * 1000
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        self.assertEqual(decrypted, original)

    def test_invalid_ciphertext_raises(self):
        with self.assertRaises(ValueError):
            decrypt_value("isto_nao_e_um_ciphertext_valido")


if __name__ == '__main__':
    unittest.main()
