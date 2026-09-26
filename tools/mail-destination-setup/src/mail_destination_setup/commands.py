from exchangelib import Account, Configuration, Credentials, DELEGATE, Folder, NTLM
from exchangelib.errors import ErrorFolderNotFound
from sqlalchemy.dialects.postgresql import insert

from mail_sort_database.models import Destination
from mail_sort_database.session import create_session_factory, session_scope

from .settings import Settings


def add_destination(settings: Settings, destination_id: str, name: str, mailbox: str, description: str) -> None:
    credentials = Credentials(username=settings.ews_username, password=settings.ews_password)
    account = Account(
        primary_smtp_address=settings.ews_username,
        config=Configuration(
            service_endpoint=settings.ews_endpoint,
            credentials=credentials,
            auth_type=NTLM,
        ),
        autodiscover=False,
        access_type=DELEGATE,
    )
    _ensure_folder(account, mailbox)

    statement = insert(Destination).values(
        id=destination_id,
        account_id=settings.mailbox_account_id,
        name=name,
        description=description,
        mailbox=mailbox,
        is_active=True,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[Destination.id],
        set_={
            "account_id": statement.excluded.account_id,
            "name": statement.excluded.name,
            "description": statement.excluded.description,
            "mailbox": statement.excluded.mailbox,
            "is_active": statement.excluded.is_active,
        },
    )
    with session_scope(create_session_factory(settings.database_url)) as session:
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
