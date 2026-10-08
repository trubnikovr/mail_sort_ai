from exchangelib import Account, Configuration, Credentials, DELEGATE, Folder, NTLM
from exchangelib.errors import ErrorFolderNotFound
from sqlalchemy.dialects.postgresql import insert

from mail_sort_database.credentials import decrypt_credential
from mail_sort_database.models import Destination, MailboxAccount
from mail_sort_database.session import create_session_factory, session_scope

from .settings import Settings


def add_destination(
    settings: Settings,
    account_id: str,
    destination_id: str,
    name: str,
    mailbox: str,
    description: str,
) -> None:
    sessions = create_session_factory(settings.database_url)
    with sessions() as session:
        account_settings = session.get(MailboxAccount, account_id)
        if account_settings is None or account_settings.provider != "ews" or not account_settings.is_configured:
            raise ValueError(f"Configured EWS mailbox account {account_id!r} was not found")
        endpoint = account_settings.host
        username = account_settings.username
        password = decrypt_credential(account_settings.encrypted_password)
        email_address = account_settings.email_address
    credentials = Credentials(username=username, password=password)
    account = Account(
        primary_smtp_address=email_address,
        config=Configuration(
            service_endpoint=endpoint,
            credentials=credentials,
            auth_type=NTLM,
        ),
        autodiscover=False,
        access_type=DELEGATE,
    )
    _ensure_folder(account, mailbox)

    statement = insert(Destination).values(
        id=destination_id,
        account_id=account_id,
        name=name,
        description=description,
        instruction=description,
        mailbox=mailbox,
        is_active=True,
        use_for_ai=True,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[Destination.id],
        set_={
            "account_id": statement.excluded.account_id,
            "name": statement.excluded.name,
            "description": statement.excluded.description,
            "instruction": statement.excluded.instruction,
            "mailbox": statement.excluded.mailbox,
            "is_active": statement.excluded.is_active,
            "use_for_ai": statement.excluded.use_for_ai,
        },
    )
    with session_scope(sessions) as session:
        session.execute(statement)


def _ensure_folder(account: Account, path: str) -> None:
    parent = account.root
    parts = [part for part in path.strip("/").split("/") if part]
    if not parts:
        raise ValueError("Destination mailbox path must not be empty")
    for part in parts:
        try:
            parent = parent / part
        except ErrorFolderNotFound:
            parent = Folder(parent=parent, name=part).save()
