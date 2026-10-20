from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import categories, rooms, ws
from app.game.graph.graph import generate_trivia


def create_app(question_source) -> FastAPI:
    """question_source: async (category) -> list[SourcedQuestion]. Tests pass a canned one."""
    app = FastAPI(title="Trivia Game Server")
    app.state.question_source = question_source
    # Dev: allow any localhost port, plus "null" for pages opened via file://
    app.add_middleware(CORSMiddleware,
                       allow_origin_regex=r"^(null|https?://(localhost|127\.0\.0\.1)(:\d+)?)$",
                       allow_methods=["*"], allow_headers=["*"])

    app.include_router(categories.router)
    app.include_router(rooms.router)
    app.include_router(ws.router)
    return app


app = create_app(generate_trivia)
