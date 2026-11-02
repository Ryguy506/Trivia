from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app import config
from app.api import categories, rooms, ws
from app.game.graph.graph import generate_trivia

# The built web app (UI/web/dist); the Dockerfile copies it here. Absent in dev and tests.
STATIC_DIR = Path(__file__).parent.parent / "static"


def create_app(question_source) -> FastAPI:
    """question_source: async (topic, difficulty) -> list[SourcedQuestion]. Tests pass a canned one."""
    app = FastAPI(title="Trivia Game Server")
    app.state.question_source = question_source
    # Dev only (DEV=1): any localhost port, plus "null" for pages opened via file://.
    # Prod serves the page and API from one address, so it needs no CORS.
    if config.DEV:
        app.add_middleware(CORSMiddleware,
                           allow_origin_regex=r"^(null|https?://(localhost|127\.0\.0\.1)(:\d+)?)$",
                           allow_methods=["*"], allow_headers=["*"])

    app.include_router(categories.router)
    app.include_router(rooms.router)
    app.include_router(ws.router)
    # Mounted last so the API routes above win; html=True serves index.html at /
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="web")
    return app


app = create_app(generate_trivia)
