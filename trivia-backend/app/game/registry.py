from app.game.room import Room
import string
import random

_rooms: dict[str, Room] = {}


def new_room_code(length: int = 4) -> str:
    while True:
        code = "".join(random.choices(string.ascii_uppercase, k=length))
        if code not in _rooms:
            return code


def new_room(room_name: str, room_description: str, topic: str, mode: str) -> Room:
    room_code = new_room_code()
    room = Room(room_code, room_name, room_description, topic, mode)
    _rooms[room_code] = room
    return room


def list_rooms() -> list[Room]:
    return list(reversed(_rooms.values()))  # dicts keep insertion order, so this is newest first


def get_room(room_code: str) -> Room | None:
    return _rooms.get(room_code.upper())
