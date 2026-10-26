from app.game.registry import new_room, get_room
from app.game.room import Room
from app.api.dto import RoomCreate, RoomOut
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/rooms", tags=["rooms"])


def to_room_out(room: Room) -> RoomOut:
    return RoomOut(
        room_code=room.room_code,
        room_name=room.room_name,
        room_description=room.room_description,
        category=room.category,
        phase=room.phase,
        players=room.player_names(),
    )


@router.get("/{room_code}")
async def find_room(room_code: str) -> RoomOut:
    room = get_room(room_code)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return to_room_out(room)


@router.post("", status_code=201)
async def create_room(body: RoomCreate) -> RoomOut:
    room = new_room(body.room_name, body.room_description, body.category)
    return to_room_out(room)


