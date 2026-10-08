from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mail_sort_database.models import Destination, Job

from ..auth import require_admin
from ..dependencies import get_session

router = APIRouter(dependencies=[Depends(require_admin)])


class DestinationInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    account_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=512)
    instruction: str = Field(default="", max_length=20_000)
    mailbox: str = Field(min_length=1, max_length=255)
    is_active: bool = True
    use_for_ai: bool = True


def serialize_destination(item: Destination) -> dict[str, Any]:
    return {
        "id": item.id,
        "account_id": item.account_id,
        "name": item.name,
        "description": item.description,
        "instruction": item.instruction,
        "mailbox": item.mailbox,
        "is_active": item.is_active,
        "use_for_ai": item.use_for_ai,
    }


@router.get("/destinations")
def list_destinations(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    destinations = session.scalars(
        select(Destination).order_by(Destination.account_id, Destination.name)
    ).all()
    return [serialize_destination(item) for item in destinations]


@router.post("/destinations", status_code=status.HTTP_201_CREATED)
def create_destination(
    payload: DestinationInput,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    destination = Destination(**payload.model_dump())
    session.add(destination)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Destination ID or mailbox already exists") from error
    session.refresh(destination)
    return serialize_destination(destination)


@router.put("/destinations/{destination_id}")
def update_destination(
    destination_id: str,
    payload: DestinationInput,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    destination = session.get(Destination, destination_id)
    if destination is None:
        raise HTTPException(status_code=404, detail="Destination not found")
    if payload.id != destination_id:
        raise HTTPException(status_code=422, detail="Destination ID cannot be changed")
    for key, value in payload.model_dump(exclude={"id"}).items():
        setattr(destination, key, value)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Destination mailbox already exists for this account") from error
    session.refresh(destination)
    return serialize_destination(destination)


@router.delete("/destinations/{destination_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_destination(destination_id: str, session: Session = Depends(get_session)) -> Response:
    destination = session.get(Destination, destination_id)
    if destination is None:
        raise HTTPException(status_code=404, detail="Destination not found")
    if session.scalar(select(Job.id).where(Job.payload["destination_id"].as_string() == destination_id).limit(1)):
        raise HTTPException(
            status_code=409,
            detail="Destination is referenced by job history; deactivate it instead",
        )
    session.delete(destination)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
