from typing import Any, Literal
import re

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mail_sort_database.credentials import encrypt_credential
from mail_sort_database.models import Destination, EmailRecord, Job, MailboxAccount

from ..auth import require_admin
from ..dependencies import get_session

router = APIRouter(dependencies=[Depends(require_admin)])


class MailboxAccountInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    provider: Literal["imap", "ews"]
    email_address: str = Field(min_length=1, max_length=255)
    source_mailbox: str = Field(default="INBOX", min_length=1, max_length=255)
    host: str = Field(min_length=1, max_length=512)
    port: int = Field(gt=0, le=65535)
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(default="", max_length=2048)
    is_active: bool = False


def serialize_account(item: MailboxAccount) -> dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "provider": item.provider,
        "email_address": item.email_address,
        "source_mailbox": item.source_mailbox,
        "host": item.host,
        "port": item.port,
        "username": item.username,
        "is_active": item.is_active,
        "is_configured": item.is_configured,
        "has_password": bool(item.encrypted_password),
    }


def _apply(account: MailboxAccount, payload: MailboxAccountInput, *, creating: bool) -> None:
    if payload.password:
        try:
            account.encrypted_password = encrypt_credential(payload.password)
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
    elif creating and not account.encrypted_password:
        raise HTTPException(status_code=422, detail="Password is required for a new mailbox account")
    for key in (
        "name", "provider", "email_address", "source_mailbox", "host", "port", "username", "is_active"
    ):
        setattr(account, key, getattr(payload, key))
    if account.is_active and not account.is_configured:
        raise HTTPException(status_code=422, detail="Complete connection settings before activating the account")


@router.get("/mailbox-accounts")
def list_mailbox_accounts(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    accounts = session.scalars(select(MailboxAccount).order_by(MailboxAccount.name)).all()
    return [serialize_account(item) for item in accounts]


@router.post("/mailbox-accounts", status_code=status.HTTP_201_CREATED)
def create_mailbox_account(
    payload: MailboxAccountInput,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    if re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", payload.id) is None:
        raise HTTPException(status_code=422, detail="New account ID may contain letters, digits, '_' and '-'")
    account = MailboxAccount(id=payload.id, name=payload.name)
    _apply(account, payload, creating=True)
    session.add(account)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Mailbox account ID already exists") from error
    session.refresh(account)
    return serialize_account(account)


@router.put("/mailbox-accounts/{account_id}")
def update_mailbox_account(
    account_id: str,
    payload: MailboxAccountInput,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    account = session.get(MailboxAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Mailbox account not found")
    if payload.id != account_id:
        raise HTTPException(status_code=422, detail="Mailbox account ID cannot be changed")
    _apply(account, payload, creating=False)
    session.commit()
    session.refresh(account)
    return serialize_account(account)


@router.delete("/mailbox-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mailbox_account(account_id: str, session: Session = Depends(get_session)) -> Response:
    account = session.get(MailboxAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Mailbox account not found")
    referenced = session.scalar(
        select(Destination.id).where(Destination.account_id == account_id).limit(1)
    ) or session.scalar(select(Job.id).where(Job.account_id == account_id).limit(1)) or session.scalar(
        select(EmailRecord.id).where(EmailRecord.account_id == account_id).limit(1)
    )
    if referenced:
        raise HTTPException(status_code=409, detail="Account is referenced by folders or job history; deactivate it instead")
    session.delete(account)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
