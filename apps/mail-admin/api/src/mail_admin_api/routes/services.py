import json
import logging
from os import getenv
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from fastapi import APIRouter, Depends

from ..auth import require_admin

logger = logging.getLogger("mail_admin.services")
router = APIRouter(dependencies=[Depends(require_admin)])

MAIL_APP_HEALTH_URL = "http://mail-app:8081/health/services"


def _read_payload(response: Any) -> dict[str, Any]:
    payload = json.loads(response.read(64_000))
    if not isinstance(payload, dict):
        return {}
    return payload


@router.get("/services")
def get_service_health() -> dict[str, Any]:
    url = getenv("MAIL_APP_HEALTH_URL", MAIL_APP_HEALTH_URL).strip()
    try:
        with urlopen(url, timeout=3) as response:
            payload = _read_payload(response)
    except HTTPError as error:
        try:
            payload = _read_payload(error)
        except (ValueError, OSError):
            payload = {}
    except (URLError, TimeoutError, OSError, ValueError) as error:
        logger.warning("mail service health unavailable: error_type=%s", type(error).__name__)
        return {"status": "unavailable", "services": {}}

    services = payload.get("services", {})
    if not isinstance(services, dict):
        services = {}
    health_status = payload.get("status")
    if health_status not in {"ready", "degraded"}:
        health_status = "unavailable"
    return {"status": health_status, "services": services}
