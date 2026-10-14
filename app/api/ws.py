from app.game.registry import get_room
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.game.graph.graph import generate_trivia

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
                    questions = await generate_trivia(room.category)
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

                await room.broadcast({"type": "chat", "player": player_name,  "text": "Answered question "})
                room.add_answer(player_name , data.get("answer_index", ""))
                if len(room.answers) == len(room.connections):
                    for player_name in room.answers.keys():
                            room.add_score(player_name)
                    room.answers = {}
                    room.next_question()
                    await room.broadcast(room.public_question())
                if room.current_index == len(room.questions) - 1:
                    await room.change_phase("results")
                    await room.broadcast({"type": "chat", "player": player_name,  "score": room.score[player_name]})
                                     
    except WebSocketDisconnect:
        room.remove_player(player_name)
        await room.broadcast({"type": "player_left", "player": player_name,
                              "players": room.player_names()})
