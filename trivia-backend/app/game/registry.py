from app.game.room import Room
import string
import random

_rooms: dict[str, Room] = {}


def new_room_code(length: int = 4) -> str:
    while True:
        code = "".join(random.choices(string.ascii_uppercase, k=length))
        if code not in _rooms:
            return code


def new_room(room_name: str, room_description: str, category: str) -> Room:
    room_code = new_room_code()
    room = Room(room_code, room_name, room_description, category)
    _rooms[room_code] = room
    return room


def get_room(room_code: str) -> Room | None:
    return _rooms.get(room_code.upper())
