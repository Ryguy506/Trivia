from app.game.registry import new_room, get_room, list_rooms
from app.game.room import Room
from app.api.dto import RoomCreate, RoomOut
from fastapi import APIRouter, HTTPException, Request
import time

router = APIRouter(prefix="/rooms", tags=["rooms"])

# Each room starts question generation, which spends the TokenRouter quota (10 requests/min)
ROOMS_PER_CLIENT = 3   # per IP, per 10 minutes
ROOMS_PER_HOUR = 20    # across everyone
_created: list[tuple[float, str]] = []  # (monotonic time, client IP) of rooms made in the last hour


def over_room_limit(ip: str) -> bool:
    now = time.monotonic()
    _created[:] = [(t, a) for t, a in _created if now - t < 3600]
    recent = sum(1 for t, a in _created if a == ip and now - t < 600)
    return recent >= ROOMS_PER_CLIENT or len(_created) >= ROOMS_PER_HOUR


def to_room_out(room: Room) -> RoomOut:
    return RoomOut(
        room_code=room.room_code,
        room_name=room.room_name,
        room_description=room.room_description,
        topic=room.topic,
        mode=room.mode,
        difficulty=room.difficulty,
        phase=room.phase,
        players=room.player_names(),
    )


# shortcut: no pagination, fine while rooms live in memory; page it if rooms persist or grow large
@router.get("")
async def all_rooms() -> list[RoomOut]:
    return [to_room_out(room) for room in list_rooms()]


@router.get("/{room_code}")
async def find_room(room_code: str) -> RoomOut:
    room = get_room(room_code)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return to_room_out(room)


@router.post("", status_code=201)
async def create_room(body: RoomCreate, request: Request) -> RoomOut:
    ip = request.client.host if request.client else "unknown"
    if over_room_limit(ip):
        raise HTTPException(status_code=429, detail="Too many rooms created. Try again in a few minutes.")
    _created.append((time.monotonic(), ip))
    room = new_room(body.room_name, body.room_description, body.topic, body.mode, body.difficulty)
    room.prepare_questions(request.app.state.question_source)
    return to_room_out(room)


