"""Whole games over real websockets, with a canned question source: no network."""
from fastapi.testclient import TestClient

from app.game.graph.schemas import SourcedQuestion
from app.main import create_app


async def canned_questions(category):
    return [SourcedQuestion(question=f"Question number {i}?", options=["A", "B", "C", "D"],
                            correct_index=0, supporting_quote="The answer is A.",
                            source_url="https://example.com") for i in range(3)]


async def failing_questions(category):
    raise RuntimeError("search is down")


def recv_until(sock, msg_type, text=None):
    while True:
        message = sock.receive_json()
        if message.get("type") == msg_type and (text is None or message.get("text") == text):
            return message


def new_room(client):
    return client.post("/rooms", json={"room_name": "Test", "category": "History"}).json()["room_code"]


def test_full_game():
    client = TestClient(create_app(canned_questions))
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}/ann") as ann, client.websocket_connect(f"/ws/{code}/bob") as bob:
        # connect returns on accept, before the server adds the player: wait until bob is in
        while recv_until(ann, "player_joined")["player"] != "bob":
            pass
        ann.send_json({"type": "start_game"})
        for i in range(3):
            assert recv_until(ann, "question")["index"] == i
            recv_until(bob, "question")
            # ann answered last in the round before: her chat must still be from ann
            ann.send_json({"type": "chat", "text": f"round {i}"})
            assert recv_until(bob, "chat", text=f"round {i}")["player"] == "ann"
            bob.send_json({"type": "submit_answer", "answer_index": 1})
            ann.send_json({"type": "submit_answer", "answer_index": 0})

        assert recv_until(ann, "results")["scores"] == {"ann": 3, "bob": 0}
        bob.close()
        assert recv_until(ann, "player_left")["players"] == ["ann"]


def test_failed_generation_returns_to_lobby():
    client = TestClient(create_app(failing_questions))
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}/ann") as ann:
        ann.send_json({"type": "start_game"})
        assert recv_until(ann, "error")["message"] == "Couldn't generate questions"
        assert recv_until(ann, "phase")["phase"] == "lobby"
