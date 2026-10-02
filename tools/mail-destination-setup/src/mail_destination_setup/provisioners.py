from abc import ABC, abstractmethod
import base64
import imaplib
import logging

from exchangelib import Account, Configuration, Credentials, DELEGATE, Folder, NTLM
from exchangelib.errors import ErrorFolderNotFound

from mail_sort_repositories import DestinationRecord

from .settings import Settings

logger = logging.getLogger(__name__)


def _imap_mailbox_name(name: str) -> str:
    """Encode non-ASCII folder names using IMAP's modified UTF-7 encoding."""
    result: list[str] = []
    non_ascii: list[str] = []

    def flush() -> None:
        if non_ascii:
            encoded = base64.b64encode("".join(non_ascii).encode("utf-16-be"))
            result.append("&" + encoded.decode("ascii").rstrip("=").replace("/", ",") + "-")
            non_ascii.clear()

    for char in name:
        code = ord(char)
        if 0x20 <= code <= 0x7E:
            flush()
            result.append("&-" if char == "&" else char)
        else:
            non_ascii.append(char)
    flush()
    return "".join(result)


class MailboxFolderProvisioner(ABC):
    @abstractmethod
    def ensure_folder(self, path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError


class ImapFolderProvisioner(MailboxFolderProvisioner):
    def __init__(self, settings: Settings) -> None:
        self._connection = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
        self._connection.login(settings.imap_username, settings.imap_app_password)
        response = self._connection.list("", '""')
        self._delimiter = "/"
        if response[0] == "OK" and response[1]:
            for row in response[1]:
                if isinstance(row, bytes):
                    marker = row.find(b'"')
                    if marker >= 0:
                        end = row.find(b'"', marker + 1)
                        if end >= 0:
                            delimiter = row[marker + 1:end]
                            if delimiter:
                                self._delimiter = delimiter.decode("ascii", errors="replace")
                            break

    def ensure_folder(self, path: str) -> None:
        parts = [part for part in path.strip("/").split("/") if part]
        if not parts:
            raise ValueError("Destination mailbox path must not be empty")
        current = ""
        for part in parts:
            current = f"{current}{self._delimiter if current else ''}{part}"
            encoded = _imap_mailbox_name(current)
            escaped = encoded.replace("\\", "\\\\").replace('"', '\\"')
            status, rows = self._connection.list("", f'"{escaped}"')
            if status != "OK":
                raise RuntimeError(f"IMAP LIST failed for destination {path!r}")
            if rows and any(row is not None for row in rows):
                continue
            status, _ = self._connection.create(f'"{escaped}"')
            if status != "OK":
                # Re-check after a concurrent provisioning attempt.
                status, rows = self._connection.list("", f'"{escaped}"')
                if status != "OK" or not rows or not any(row is not None for row in rows):
                    raise RuntimeError(f"Could not create IMAP folder {current!r}")
            logger.info("IMAP folder ready: %s", current)

    def close(self) -> None:
        try:
            self._connection.logout()
        except imaplib.IMAP4.error:
            pass


class EwsFolderProvisioner(MailboxFolderProvisioner):
    def __init__(self, settings: Settings) -> None:
        credentials = Credentials(username=settings.ews_username, password=settings.ews_password)
        self._account = Account(
            primary_smtp_address=settings.ews_username,
            config=Configuration(service_endpoint=settings.ews_endpoint,
                                 credentials=credentials, auth_type=NTLM),
            autodiscover=False, access_type=DELEGATE,
        )

    def ensure_folder(self, path: str) -> None:
        parts = [part.strip() for part in path.strip("/").split("/") if part.strip()]
        if not parts:
            raise ValueError("Destination mailbox path must not be empty")
        parent = self._account.root
        if parts[0].casefold() == "inbox":
            parent = self._account.inbox
            parts = parts[1:]
        for part in parts:
            try:
                parent = parent / part
            except ErrorFolderNotFound:
                parent = Folder(parent=parent, name=part).save()
                logger.info("EWS folder created: %s", part)

    def close(self) -> None:
        pass


def build_provisioner(settings: Settings) -> MailboxFolderProvisioner:
    if settings.mailbox_provider == "imap":
        return ImapFolderProvisioner(settings)
    if settings.mailbox_provider == "ews":
        return EwsFolderProvisioner(settings)
    raise ValueError(f"Unsupported mailbox provider: {settings.mailbox_provider}")


def provision_catalog(settings: Settings,
                      destinations: tuple[DestinationRecord, ...]) -> None:
    provisioner = build_provisioner(settings)
    try:
        for destination in destinations:
            if not destination.enabled:
                continue
            provisioner.ensure_folder(destination.mailbox)
            logger.info("Destination folder ready: id=%s path=%s",
                        destination.id, destination.mailbox)
    finally:
        provisioner.close()
