import asyncio
import json
import logging

from app.game.registry import get_room
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

# Below this a narrow topic makes too short a game; the host is asked for a broader one
MIN_QUESTIONS = 5


@router.websocket("/ws/{room_code}/{player_name}")
async def room_socket(websocket: WebSocket, room_code: str, player_name: str):
    await websocket.accept()

    room = get_room(room_code)
    if room is None:
        await websocket.close(code=4004, reason="Room not found")
        return
    if room.has_player(player_name):
        await websocket.close(code=4009, reason="Name already taken")
        return

    room.add_player(player_name, websocket)
    await room.broadcast({"type": "player_joined", "player": player_name,
                          "players": room.player_names(), "host": room.host})

    try:
        while True:
            # Clients are untrusted: skip anything that isn't a JSON object instead of crashing the socket
            try:
                data = json.loads(await websocket.receive_text())
            except ValueError:
                continue
            if not isinstance(data, dict):
                continue
            if data.get("type") == "start_game":
                # ignore non-hosts, double-clicks and restarts mid-game
                if room.phase != "lobby" or player_name != room.host:
                    continue
                await room.change_phase("generating")  # questions usually ready already; the spinner covers the rest
                try:
                    questions = await room.questions_task
                except Exception:
                    logger.exception("Question generation failed for room %s", room.room_code)
                    questions = []
                if len(questions) < MIN_QUESTIONS:
                    await room.broadcast({"type": "error",
                                          "message": "Not enough material for that topic. Try something broader."})
                    room.prepare_questions(websocket.app.state.question_source)  # fresh attempt for the next Start
                    await room.change_phase("lobby")
                    continue
                room.set_questions(questions)
                await room.change_phase("question")
                await room.broadcast(room.public_question())
                room.timer_task = asyncio.create_task(room.run_timer())

            elif data.get("type") == "chat":
                await room.broadcast({"type": "chat", "player": player_name,
                                      "text": data.get("text", "")})
            elif data.get("type") == "submit_answer":
                await room.broadcast({"type": "chat", "player": player_name, "text": "Answered question "})
                for message in room.submit_answer(player_name, data.get("answer_index")):
                    await room.broadcast(message)

    except WebSocketDisconnect:
        pass
    finally:
        # Runs on any exit, so a crashed handler can't leave a ghost player holding the round and name
        follow_ups = room.remove_player(player_name)
        await room.broadcast({"type": "player_left", "player": player_name,
                              "players": room.player_names(), "host": room.host})
        for message in follow_ups:
            await room.broadcast(message)
