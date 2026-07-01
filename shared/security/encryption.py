"""AES-256-GCM encryption utility for stored credentials.

Security hardening (Proposal §10.2 H2/H3): encrypts sensitive fields
like SMTP passwords and webhook tokens before database write,
decrypts only at use time.

Uses AES-256-GCM with a key derived from SECRET_KEY via SHA-256.
"""
import base64
import hashlib
import os
import secrets
from typing import Optional


def _derive_key(secret_key: str) -> bytes:
    """Derive a 32-byte AES-256 key from the platform SECRET_KEY."""
    return hashlib.sha256(secret_key.encode()).digest()


def encrypt_value(plaintext: str, secret_key: str) -> Optional[str]:
    """Encrypt a string value using AES-256-GCM.

    Args:
        plaintext: The value to encrypt.
        secret_key: The platform SECRET_KEY for key derivation.

    Returns:
        Base64-encoded ciphertext with nonce prepended, or None on failure.
    """
    if not plaintext or not secret_key:
        return None

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = _derive_key(secret_key)
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        # Prepend nonce to ciphertext for storage
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode()
    except ImportError:
        # Fallback: basic XOR obfuscation (not cryptographically secure,
        # but better than plaintext for dev environments without cryptography)
        key = _derive_key(secret_key)
        result = bytes(a ^ b for a, b in zip(plaintext.encode(), key * (len(plaintext) // len(key) + 1)))
        return base64.b64encode(result).decode()


def decrypt_value(ciphertext_b64: str, secret_key: str) -> Optional[str]:
    """Decrypt a value encrypted with encrypt_value().

    Args:
        ciphertext_b64: Base64-encoded ciphertext with nonce.
        secret_key: The platform SECRET_KEY for key derivation.

    Returns:
        Decrypted plaintext string, or None on failure.
    """
    if not ciphertext_b64 or not secret_key:
        return None

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = _derive_key(secret_key)
        combined = base64.b64decode(ciphertext_b64)
        nonce = combined[:12]
        ciphertext = combined[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode()
    except ImportError:
        # Fallback: reverse XOR obfuscation
        try:
            key = _derive_key(secret_key)
            combined = base64.b64decode(ciphertext_b64)
            result = bytes(a ^ b for a, b in zip(combined, key * (len(combined) // len(key) + 1)))
            return result.decode()
        except Exception:
            return None
    except Exception:
        return None


def is_encrypted(value: str) -> bool:
    """Heuristic check: does a stored value look encrypted?"""
    try:
        decoded = base64.b64decode(value)
        return len(decoded) >= 12  # At minimum a nonce
    except Exception:
        return False