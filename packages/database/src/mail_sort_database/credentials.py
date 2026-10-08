from os import getenv

from cryptography.fernet import Fernet


def _fernet() -> Fernet:
    key = getenv("MAILBOX_CREDENTIALS_KEY", "").strip()
    if not key:
        raise RuntimeError("MAILBOX_CREDENTIALS_KEY must be configured to manage mailbox passwords")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as error:
        raise RuntimeError("MAILBOX_CREDENTIALS_KEY must be a valid Fernet key") from error


def encrypt_credential(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_credential(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


def generate_credentials_key() -> str:
    """Return a Fernet key suitable for MAILBOX_CREDENTIALS_KEY."""
    return Fernet.generate_key().decode()
