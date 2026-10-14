from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import categories, rooms, ws

app = FastAPI(title="Trivia Game Server")
# Dev: allow any localhost port, plus "null" for pages opened via file://
app.add_middleware(CORSMiddleware,
                   allow_origin_regex=r"^(null|https?://(localhost|127\.0\.0\.1)(:\d+)?)$",
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(categories.router)
app.include_router(rooms.router)
app.include_router(ws.router)