from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mail_sort_database.models import AppSetting

from ..auth import require_admin
from ..dependencies import get_session

router = APIRouter(dependencies=[Depends(require_admin)])

DECISION_ENABLED_KEY = "mail_decision.enabled"
DECISION_ENABLED_DESCRIPTION = "Controls whether Decision claims new classification jobs."


class SettingValue(BaseModel):
    value: bool


def serialize_decision_setting(setting: AppSetting | None) -> dict[str, Any]:
    return {
        "key": DECISION_ENABLED_KEY,
        "value": True if setting is None else setting.value is True,
        "description": DECISION_ENABLED_DESCRIPTION,
        "updated_at": setting.updated_at if setting is not None else None,
    }


@router.get("/settings")
def get_settings(session: Session = Depends(get_session)) -> dict[str, Any]:
    return serialize_decision_setting(session.get(AppSetting, DECISION_ENABLED_KEY))


@router.put("/settings/mail_decision.enabled")
def set_decision_enabled(
    payload: SettingValue,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    setting = session.get(AppSetting, DECISION_ENABLED_KEY)
    if setting is None:
        setting = AppSetting(
            key=DECISION_ENABLED_KEY,
            value=payload.value,
            description=DECISION_ENABLED_DESCRIPTION,
        )
        session.add(setting)
    else:
        setting.value = payload.value
    session.commit()
    session.refresh(setting)
    return serialize_decision_setting(setting)
