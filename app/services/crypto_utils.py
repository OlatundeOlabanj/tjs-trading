"""
Fernet symmetric encryption for Bybit API key storage.
MASTER_KEY must be set as environment variable — never hardcoded.
Generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import os
from cryptography.fernet import Fernet


def get_fernet() -> Fernet:
    key = os.environ.get("MASTER_KEY")
    if not key:
        raise RuntimeError(
            "MASTER_KEY not set. Generate with: "
            "python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode())


def encrypt(plain: str) -> str:
    return get_fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    return get_fernet().decrypt(token.encode()).decode()


def generate_master_key() -> str:
    return Fernet.generate_key().decode()
