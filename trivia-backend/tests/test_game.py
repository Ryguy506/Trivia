"""Whole games over real websockets, with a canned question source: no network."""
import pytest
from fastapi.testclient import TestClient

from app.game import room as room_module
from app.game.graph.schemas import SourcedQuestion
from app.main import create_app


def canned(count):
    async def source(topic, difficulty):
        return [SourcedQuestion(question=f"Question number {i}?", options=["A", "B", "C", "D"],
                                correct_index=0, supporting_quote="The answer is A.",
                                source_url="https://example.com") for i in range(count)]
    return source


canned_questions = canned(5)
TOO_FEW = "Not enough material for that topic. Try something broader."


async def failing_questions(topic, difficulty):
    raise RuntimeError("search is down")


@pytest.fixture(autouse=True)
def short_reveal(monkeypatch):
    # long enough that every round_result is sent before run_timer sends the next question
    monkeypatch.setattr(room_module, "REVEAL_SECONDS", 0.01)


@pytest.fixture
def make_client():
    """Clients run as `with` blocks: one event loop for all requests, so the generation task
    started by POST /rooms is still alive when start_game awaits it (as on the real server)."""
    clients = []

    def make(question_source):
        clients.append(TestClient(create_app(question_source)).__enter__())
        return clients[-1]
    yield make
    for client in clients:
        client.__exit__(None, None, None)


def recv_until(sock, msg_type, text=None):
    while True:
        message = sock.receive_json()
        if message.get("type") == msg_type and (text is None or message.get("text") == text):
            return message


def new_room(client):
    return client.post("/rooms", json={"room_name": "Test", "topic": "History"}).json()["room_code"]


def test_full_game(make_client):
    client = make_client(canned_questions)
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
            assert recv_until(bob, "round_result")["correct_index"] == 0

        assert recv_until(ann, "results")["scores"] == {"ann": 5, "bob": 0}
        bob.close()
        assert recv_until(ann, "player_left")["players"] == ["ann"]


def test_failed_generation_returns_to_lobby(make_client):
    client = make_client(failing_questions)
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}/ann") as ann:
        ann.send_json({"type": "start_game"})
        assert recv_until(ann, "error")["message"] == TOO_FEW
        assert recv_until(ann, "phase")["phase"] == "lobby"


def test_topic_is_trimmed_and_echoed(make_client):
    client = make_client(canned_questions)
    res = client.post("/rooms", json={"room_name": "Test", "topic": "  90s hip hop "})
    assert res.status_code == 201 and res.json()["topic"] == "90s hip hop"


def test_bad_topic_is_rejected(make_client):
    client = make_client(canned_questions)
    for body in [{"topic": "   "}, {"topic": "x"}, {"topic": "x" * 81}, {}, {"category": "History"}]:
        assert client.post("/rooms", json={"room_name": "Test", **body}).status_code == 422, body


def test_categories_unchanged(make_client):
    assert len(make_client(canned_questions).get("/categories").json()) == 10


def test_question_source_gets_room_topic_and_difficulty(make_client):
    seen = []

    async def recording_source(topic, difficulty):
        seen.append((topic, difficulty))
        return await canned_questions(topic, difficulty)

    client = make_client(recording_source)
    res = client.post("/rooms", json={"room_name": "Test", "topic": " volcanoes ", "difficulty": "hard"})
    assert res.json()["difficulty"] == "hard"
    with client.websocket_connect(f"/ws/{res.json()['room_code']}/ann") as ann:
        ann.send_json({"type": "start_game"})
        recv_until(ann, "question")
    assert seen == [("volcanoes", "hard")]


def test_difficulty_defaults_to_medium_and_rejects_unknown(make_client):
    client = make_client(canned_questions)
    assert client.post("/rooms", json={"room_name": "Test", "topic": "History"}).json()["difficulty"] == "medium"
    assert client.post("/rooms", json={"room_name": "Test", "topic": "History", "difficulty": "insane"}).status_code == 422


def test_too_few_questions_returns_to_lobby_and_can_restart(make_client):
    client = make_client(canned(4))
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}/ann") as ann:
        ann.send_json({"type": "start_game"})
        assert recv_until(ann, "error")["message"] == TOO_FEW
        assert recv_until(ann, "phase")["phase"] == "lobby"
        ann.send_json({"type": "start_game"})
        assert recv_until(ann, "phase")["phase"] == "generating"
        assert recv_until(ann, "error")["message"] == TOO_FEW


def test_malformed_messages_are_skipped_and_leaver_is_removed(make_client):
    client = make_client(canned_questions)
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


def test_generation_failure_is_logged(caplog, make_client):
    client = make_client(failing_questions)
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}/ann") as ann:
        ann.send_json({"type": "start_game"})
        recv_until(ann, "error")
    assert "search is down" in caplog.text


def test_mode_defaults_to_trivia_and_rejects_unknown(make_client):
    client = make_client(canned_questions)
    assert client.post("/rooms", json={"room_name": "Test", "topic": "History"}).json()["mode"] == "trivia"
    assert client.post("/rooms", json={"room_name": "Test", "topic": "History", "mode": "trivia"}).status_code == 201
    assert client.post("/rooms", json={"room_name": "Test", "topic": "History", "mode": "chess"}).status_code == 422


def test_room_list_is_newest_first(make_client):
    client = make_client(canned_questions)
    first, second = new_room(client), new_room(client)
    rooms = client.get("/rooms").json()
    assert [r["room_code"] for r in rooms[:2]] == [second, first]
    assert {"mode", "phase", "players", "topic"} <= rooms[0].keys()


def test_generation_starts_when_the_room_is_created(make_client):
    seen = []

    async def recording_source(topic, difficulty):
        seen.append(topic)
        return await canned_questions(topic, difficulty)

    client = make_client(recording_source)
    code = client.post("/rooms", json={"room_name": "Test", "topic": "volcanoes"}).json()["room_code"]
    client.get(f"/rooms/{code}")  # one more request lets the loop run the new task
    assert seen == ["volcanoes"]  # before anyone joined or pressed Start


def test_join_and_leave_messages_name_the_host(make_client):
    client = make_client(canned_questions)
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}/ann") as ann:
        assert recv_until(ann, "player_joined")["host"] == "ann"  # her own join already says so
        with client.websocket_connect(f"/ws/{code}/bob") as bob:
            assert recv_until(bob, "player_joined")["host"] == "ann"
            ann.close()
            assert recv_until(bob, "player_left")["host"] == "bob"


def test_only_the_host_can_start(make_client):
    client = make_client(canned_questions)
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}/ann") as ann, client.websocket_connect(f"/ws/{code}/bob") as bob:
        while recv_until(ann, "player_joined")["player"] != "bob":
            pass
        bob.send_json({"type": "start_game"})
        bob.send_json({"type": "chat", "text": "after start"})
        # messages from one socket are handled in order: bob's start was ignored before his chat
        message = ann.receive_json()
        assert message == {"type": "chat", "player": "bob", "text": "after start"}
        ann.send_json({"type": "start_game"})
        assert recv_until(bob, "phase")["phase"] == "generating"
