from app.game.registry import get_room
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


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
                          "players": room.player_names()})

    try:
        while True:
            data = await websocket.receive_json()
            # For now just relay chat messages; game actions (answers, start game) go here later
            if data.get("type") == "start_game":
                if room.phase != "lobby":  # ignore double-clicks / restarts mid-game
                    continue
                await room.change_phase("generating")
                try:
                    questions = await websocket.app.state.question_source(room.category)
                except Exception:
                    questions = []
                if not questions:
                    await room.broadcast({"type": "error", "message": "Couldn't generate questions"})
                    await room.change_phase("lobby")
                    continue
                room.set_questions(questions)
                await room.change_phase("question")
                await room.broadcast(room.public_question())

            elif data.get("type") == "chat":
                await room.broadcast({"type": "chat", "player": player_name,
                                      "text": data.get("text", "")})
            elif data.get("type") == "submit_answer":
                await room.broadcast({"type": "chat", "player": player_name, "text": "Answered question "})
                for message in room.submit_answer(player_name, data.get("answer_index")):
                    await room.broadcast(message)

    except WebSocketDisconnect:
        follow_ups = room.remove_player(player_name)
        await room.broadcast({"type": "player_left", "player": player_name,
                              "players": room.player_names()})
        for message in follow_ups:
            await room.broadcast(message)
