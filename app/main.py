import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text

from app.config import DEFAULT_SECRET, get_settings
from app.deps import Session
from app.routers import admin, auth, feed, links, posts

log = logging.getLogger("uvicorn.error")
settings = get_settings()

app = FastAPI(
    title="Portfolio API",
    description="Blog posts, notes and reading list behind Anish Tilloo's portfolio.",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.secret_key == DEFAULT_SECRET:
    log.warning("SECRET_KEY is still the default. Set a real one in backend/.env before deploying.")

for router in (auth.router, posts.router, links.router, feed.router, admin.router):
    app.include_router(router)


@app.get("/api/health", tags=["meta"])
async def health(session: Session) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


def serve_frontend(dist: Path) -> None:
    """Serve the built Vue app, sending unknown paths to index.html for the router."""
    index = dist / "index.html"
    root = dist.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index)


if (settings.frontend_dist / "index.html").is_file():
    serve_frontend(settings.frontend_dist)
