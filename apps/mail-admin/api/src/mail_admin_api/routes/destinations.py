from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from mail_sort_database.models import Destination

from ..auth import require_admin
from ..dependencies import get_session

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/destinations")
def list_destinations(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    destinations = session.scalars(
        select(Destination).order_by(Destination.account_id, Destination.name)
    ).all()
    return [{
        "id": item.id,
        "account_id": item.account_id,
        "name": item.name,
        "description": item.description,
        "instruction": item.instruction,
        "mailbox": item.mailbox,
        "is_active": item.is_active,
        "use_for_ai": item.use_for_ai,
    } for item in destinations]
