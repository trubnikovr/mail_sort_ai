import logging
from os import getenv
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from mail_sort_database.session import create_session_factory
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from .auth import LoginRateLimiter, router as auth_router
from .routes import dashboard, destinations, jobs, logs, services, settings as settings_routes
from .settings import Settings

logger = logging.getLogger("mail_admin")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    app = FastAPI(
        title="Mail Sort Admin API",
        version="0.1.0",
        description="Operational dashboard and message review API for Mail Sort.",
    )
    app.state.settings = settings
    app.state.login_rate_limiter = LoginRateLimiter()
    app.state.session_factory = create_session_factory(settings.database_url)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="mail_sort_admin_session",
        max_age=settings.session_max_age_seconds,
        same_site="lax",
        https_only=settings.cookie_secure,
    )
    app.include_router(auth_router, prefix="/api", tags=["auth"])
    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
    app.include_router(jobs.router, prefix="/api", tags=["jobs"])
    app.include_router(logs.router, prefix="/api", tags=["logs"])
    app.include_router(settings_routes.router, prefix="/api", tags=["settings"])
    app.include_router(destinations.router, prefix="/api", tags=["destinations"])
    app.include_router(services.router, prefix="/api", tags=["services"])

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        with app.state.session_factory() as session:
            session.execute(text("SELECT 1"))
        return {"status": "ok"}

    default_web_dist = Path(__file__).resolve().parents[3] / "web" / "dist"
    web_dist = Path(getenv("MAIL_ADMIN_WEB_DIST", str(default_web_dist)))
    if web_dist.is_dir():
        assets = web_dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="admin-assets")

        @app.get("/{frontend_path:path}", include_in_schema=False)
        def frontend(frontend_path: str) -> FileResponse:
            index = web_dist / "index.html"
            return FileResponse(index)

    return app


def run() -> None:
    settings = Settings.from_environment()
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=settings.host, port=settings.port)


app = create_app()


if __name__ == "__main__":
    run()
