from app.game.registry import new_room, get_room, list_rooms
from app.game.room import Room
from app.api.dto import RoomCreate, RoomOut
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/rooms", tags=["rooms"])


def to_room_out(room: Room) -> RoomOut:
    return RoomOut(
        room_code=room.room_code,
        room_name=room.room_name,
        room_description=room.room_description,
        topic=room.topic,
        mode=room.mode,
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
async def create_room(body: RoomCreate) -> RoomOut:
    room = new_room(body.room_name, body.room_description, body.topic, body.mode)
    return to_room_out(room)


