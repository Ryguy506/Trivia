"""Whole games over real websockets, with a canned question source: no network."""
from fastapi.testclient import TestClient

from app.game.graph.schemas import SourcedQuestion
from app.main import create_app


def canned(count):
    async def source(topic):
        return [SourcedQuestion(question=f"Question number {i}?", options=["A", "B", "C", "D"],
                                correct_index=0, supporting_quote="The answer is A.",
                                source_url="https://example.com") for i in range(count)]
    return source


canned_questions = canned(5)
TOO_FEW = "Not enough material for that topic. Try something broader."


async def failing_questions(topic):
    raise RuntimeError("search is down")


def recv_until(sock, msg_type, text=None):
    while True:
        message = sock.receive_json()
        if message.get("type") == msg_type and (text is None or message.get("text") == text):
            return message


def new_room(client):
    return client.post("/rooms", json={"room_name": "Test", "topic": "History"}).json()["room_code"]


def test_full_game():
    client = TestClient(create_app(canned_questions))
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}/ann") as ann, client.websocket_connect(f"/ws/{code}/bob") as bob:
        # connect returns on accept, before the server adds the player: wait until bob is in
        while recv_until(ann, "player_joined")["player"] != "bob":
            pass
        ann.send_json({"type": "start_game"})
        for i in range(5):
            assert recv_until(ann, "question")["index"] == i
            recv_until(bob, "question")
            # ann answered last in the round before: her chat must still be from ann
            ann.send_json({"type": "chat", "text": f"round {i}"})
            assert recv_until(bob, "chat", text=f"round {i}")["player"] == "ann"
            bob.send_json({"type": "submit_answer", "answer_index": 1})
            ann.send_json({"type": "submit_answer", "answer_index": 0})

        assert recv_until(ann, "results")["scores"] == {"ann": 5, "bob": 0}
        bob.close()
        assert recv_until(ann, "player_left")["players"] == ["ann"]


def test_failed_generation_returns_to_lobby():
    client = TestClient(create_app(failing_questions))
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}/ann") as ann:
        ann.send_json({"type": "start_game"})
        assert recv_until(ann, "error")["message"] == TOO_FEW
        assert recv_until(ann, "phase")["phase"] == "lobby"


def test_topic_is_trimmed_and_echoed():
    client = TestClient(create_app(canned_questions))
    res = client.post("/rooms", json={"room_name": "Test", "topic": "  90s hip hop "})
    assert res.status_code == 201 and res.json()["topic"] == "90s hip hop"


def test_bad_topic_is_rejected():
    client = TestClient(create_app(canned_questions))
    for body in [{"topic": "   "}, {"topic": "x"}, {"topic": "x" * 81}, {}, {"category": "History"}]:
        assert client.post("/rooms", json={"room_name": "Test", **body}).status_code == 422, body


def test_categories_unchanged():
    assert len(TestClient(create_app(canned_questions)).get("/categories").json()) == 10


def test_question_source_gets_room_topic():
    seen = []

    async def recording_source(topic):
        seen.append(topic)
        return await canned_questions(topic)

    client = TestClient(create_app(recording_source))
    code = client.post("/rooms", json={"room_name": "Test", "topic": " volcanoes "}).json()["room_code"]
    with client.websocket_connect(f"/ws/{code}/ann") as ann:
        ann.send_json({"type": "start_game"})
        recv_until(ann, "question")
    assert seen == ["volcanoes"]


def test_too_few_questions_returns_to_lobby_and_can_restart():
    client = TestClient(create_app(canned(4)))
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}/ann") as ann:
        ann.send_json({"type": "start_game"})
        assert recv_until(ann, "error")["message"] == TOO_FEW
        assert recv_until(ann, "phase")["phase"] == "lobby"
        ann.send_json({"type": "start_game"})
        assert recv_until(ann, "phase")["phase"] == "generating"
        assert recv_until(ann, "error")["message"] == TOO_FEW


def test_malformed_messages_are_skipped_and_leaver_is_removed():
    client = TestClient(create_app(canned_questions))
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}/ann") as ann, client.websocket_connect(f"/ws/{code}/bob") as bob:
        while recv_until(bob, "player_joined")["player"] != "bob":
            pass
        ann.send_text("not json")
        ann.send_json([1, 2])
        ann.send_json({"type": "chat", "text": "still here"})
        assert recv_until(bob, "chat", text="still here")["player"] == "ann"
        ann.close()
        assert recv_until(bob, "player_left")["players"] == ["bob"]


def test_generation_failure_is_logged(caplog):
    client = TestClient(create_app(failing_questions))
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}/ann") as ann:
        ann.send_json({"type": "start_game"})
        recv_until(ann, "error")
    assert "search is down" in caplog.text


def test_mode_defaults_to_trivia_and_rejects_unknown():
    client = TestClient(create_app(canned_questions))
    assert client.post("/rooms", json={"room_name": "Test", "topic": "History"}).json()["mode"] == "trivia"
    assert client.post("/rooms", json={"room_name": "Test", "topic": "History", "mode": "trivia"}).status_code == 201
    assert client.post("/rooms", json={"room_name": "Test", "topic": "History", "mode": "chess"}).status_code == 422


def test_room_list_is_newest_first():
    client = TestClient(create_app(canned_questions))
    first, second = new_room(client), new_room(client)
    rooms = client.get("/rooms").json()
    assert [r["room_code"] for r in rooms[:2]] == [second, first]
    assert {"mode", "phase", "players", "topic"} <= rooms[0].keys()
