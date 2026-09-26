"""Provider-neutral extraction of plain-text email content."""

from email.message import Message
import re


def extract_body(message: Message) -> str:
    """Keep only text/plain parts and never include attachment content."""
    plain_parts: list[str] = []
    parts = message.walk() if message.is_multipart() else (message,)
    for part in parts:
        if part.get_content_disposition() == "attachment":
            continue
        content_type = part.get_content_type()
        if content_type == "text/plain":
            plain_parts.append(str(part.get_content()))

    return normalize_whitespace("\n".join(plain_parts))


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
