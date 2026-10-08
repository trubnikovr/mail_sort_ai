from collections import defaultdict, deque
from hmac import compare_digest
from threading import Lock
from time import monotonic

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from starlette.responses import Response

from .settings import Settings

router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


class LoginRateLimiter:
    """Limit failed logins per client address in this single-instance admin app."""

    _MAX_ATTEMPTS = 5
    _WINDOW_SECONDS = 900

    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, client: str) -> int:
        now = monotonic()
        with self._lock:
            attempts = self._attempts[client]
            while attempts and now - attempts[0] >= self._WINDOW_SECONDS:
                attempts.popleft()
            if len(attempts) >= self._MAX_ATTEMPTS:
                return max(1, int(self._WINDOW_SECONDS - (now - attempts[0])))
            return 0

    def fail(self, client: str) -> None:
        with self._lock:
            self._attempts[client].append(monotonic())

    def clear(self, client: str) -> None:
        with self._lock:
            self._attempts.pop(client, None)


def require_admin(request: Request) -> str:
    username = request.session.get("admin_username")
    if not isinstance(username, str) or not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return username


@router.get("/auth/me")
def current_admin(request: Request) -> dict[str, str | bool]:
    username = request.session.get("admin_username")
    if not isinstance(username, str) or not username:
        return {"authenticated": False}
    return {"authenticated": True, "username": username}


@router.post("/auth/login")
def login(credentials: LoginRequest, request: Request) -> dict[str, str | bool]:
    client = request.client.host if request.client else "unknown"
    retry_after = request.app.state.login_rate_limiter.check(client)
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed sign-in attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    settings: Settings = request.app.state.settings
    valid_username = compare_digest(credentials.username.encode(), settings.admin_username.encode())
    valid_password = compare_digest(credentials.password.encode(), settings.admin_password.encode())
    if not (valid_username and valid_password):
        request.app.state.login_rate_limiter.fail(client)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    request.app.state.login_rate_limiter.clear(client)
    request.session.clear()
    request.session["admin_username"] = settings.admin_username
    return {"authenticated": True, "username": settings.admin_username}


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
