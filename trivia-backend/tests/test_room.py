import asyncio

import pytest

from app.game import room as room_module
from app.game.graph.schemas import SourcedQuestion
from app.game.room import Room


class FakeSocket:
    def __init__(self):
        self.dead = False
        self.sent = []

    async def send_json(self, message):
        if self.dead:
            raise RuntimeError("socket closed")
        self.sent.append(message)


def make_question() -> SourcedQuestion:
    return SourcedQuestion(question="Which letter is right?", options=["A", "B", "C", "D"],
                           correct_index=0, supporting_quote="The answer is A.",
                           source_url="https://example.com")


def make_room(players=("ann", "bob"), num_questions=2) -> Room:
    """A room mid-game, on the first question."""
    room = Room("ABCD", "Test room", "", "History", "trivia")
    for name in players:
        room.add_player(name, FakeSocket())
    room.set_questions([make_question() for _ in range(num_questions)])
    room.phase = "question"
    return room


def test_round_waits_for_every_player():
    room = make_room()
    assert room.submit_answer("ann", 0) == []
    assert room.current_index == 0


def test_round_end_reveals_the_answer_and_waits():
    room = make_room()
    room.submit_answer("ann", 0)
    messages = room.submit_answer("bob", 1)
    # only the right answer goes out: nobody's pick is sent
    assert messages == [{"type": "round_result", "index": 0, "correct_index": 0,
                         "supporting_quote": "The answer is A.", "source_url": "https://example.com",
                         "scores": {"ann": 1, "bob": 0}}]
    assert room.current_index == 0 and room.phase == "question"


def test_advance_after_the_reveal_sends_the_next_question():
    room = make_room()
    room.submit_answer("ann", 0)
    room.submit_answer("bob", 1)
    assert room.advance() == [{"type": "question", "index": 1, "total": 2,
                               "question": "Which letter is right?", "options": ["A", "B", "C", "D"],
                               "seconds": 30}]


def test_answer_during_the_reveal_is_ignored():
    room = make_room()
    room.submit_answer("ann", 0)
    room.submit_answer("bob", 1)
    assert room.submit_answer("bob", 0) == []  # before run_timer starts the next round
    assert room.answers == {} and room.score == {"ann": 1, "bob": 0}


def test_game_ends_after_last_question_is_answered():
    room = make_room(num_questions=2)
    for _ in range(2):
        room.round_ended.clear()  # run_timer does this at the start of each round
        room.submit_answer("ann", 0)
        room.submit_answer("bob", 1)
        messages = room.advance()
    assert room.phase == "results"
    assert messages == [{"type": "phase", "phase": "results"},
                        {"type": "results", "scores": {"ann": 2, "bob": 0}}]


def test_one_question_game_waits_for_the_second_player():
    room = make_room(num_questions=1)
    assert room.submit_answer("ann", 0) == []
    assert room.phase == "question"


def test_first_answer_is_final():
    room = make_room(num_questions=1)
    room.submit_answer("ann", 0)
    assert room.submit_answer("ann", 1) == []
    messages = room.submit_answer("bob", 1)
    assert messages[0]["scores"] == {"ann": 1, "bob": 0}


@pytest.mark.parametrize("answer", [None, "", "0", 1.0, True, -1, 4])
def test_invalid_answer_is_ignored(answer):
    room = make_room()
    assert room.submit_answer("ann", answer) == []
    assert room.answers == {}


def test_answer_outside_question_phase_is_ignored():
    room = make_room()
    room.phase = "lobby"
    assert room.submit_answer("ann", 0) == []
    assert room.answers == {}


def test_answer_from_unknown_player_is_ignored():
    room = make_room()
    assert room.submit_answer("mallory", 0) == []
    assert room.answers == {}


def test_player_leaving_ends_round_the_others_finished():
    room = make_room(players=("ann", "bob", "cat"))
    room.submit_answer("ann", 0)
    room.submit_answer("bob", 0)
    assert [m["type"] for m in room.remove_player("cat")] == ["round_result"]
    assert room.score == {"ann": 1, "bob": 1, "cat": 0}


def test_player_who_left_keeps_their_score():
    room = make_room(num_questions=1)
    room.submit_answer("ann", 0)
    assert room.remove_player("ann") == []
    messages = room.submit_answer("bob", 1)
    assert messages[0]["scores"] == {"ann": 1, "bob": 0}


def test_last_player_leaving_sends_nothing():
    room = make_room(players=("ann",))
    assert room.remove_player("ann") == []
    assert room.remove_player("ann") == []


def test_dropped_sockets_during_broadcast_end_the_round():
    room = make_room(players=("ann", "bob", "cat", "dan"))
    room.submit_answer("ann", 0)
    room.submit_answer("bob", 0)
    room.connections["cat"].dead = True
    room.connections["dan"].dead = True
    ann = room.connections["ann"]

    chat = {"type": "chat", "player": "ann", "text": "hi"}
    asyncio.run(room.broadcast(chat))

    assert room.player_names() == ["ann", "bob"]
    assert [m["type"] for m in ann.sent] == ["chat", "round_result"]
    assert room.score == {"ann": 1, "bob": 1, "cat": 0, "dan": 0}


def test_timer_ends_rounds_nobody_finished(monkeypatch):
    monkeypatch.setattr(room_module, "REVEAL_SECONDS", 0)
    room = make_room(num_questions=2)
    room.timer = 0.01
    room.submit_answer("ann", 0)  # bob never answers

    asyncio.run(room.run_timer())  # returns once the game reaches results

    assert room.phase == "results"
    bob = room.connections["bob"]
    assert [m["type"] for m in bob.sent] == ["round_result", "question", "round_result", "phase", "results"]
    assert bob.sent[-1]["scores"] == {"ann": 1, "bob": 0}


def test_finishing_early_restarts_the_timer_for_the_next_question(monkeypatch):
    monkeypatch.setattr(room_module, "REVEAL_SECONDS", 0)
    room = make_room(num_questions=2)
    room.timer = 0.2

    async def play():
        task = asyncio.create_task(room.run_timer())
        await asyncio.sleep(0.1)
        room.submit_answer("ann", 0)
        room.submit_answer("bob", 0)
        await asyncio.sleep(0.15)  # past the first question's deadline, inside the second's
        assert room.current_index == 1
        task.cancel()

    asyncio.run(play())


def test_next_question_comes_after_the_reveal_pause(monkeypatch):
    monkeypatch.setattr(room_module, "REVEAL_SECONDS", 0.2)
    room = make_room(num_questions=2)

    async def play():
        task = asyncio.create_task(room.run_timer())
        await asyncio.sleep(0)  # let run_timer start the round
        room.submit_answer("ann", 0)
        room.submit_answer("bob", 0)
        await asyncio.sleep(0.1)
        assert room.current_index == 0  # still revealing
        await asyncio.sleep(0.2)
        assert room.current_index == 1
        task.cancel()

    asyncio.run(play())


def test_first_player_to_join_is_host():
    room = make_room(players=("ann", "bob"))
    assert room.host == "ann"


def test_host_passes_to_the_longest_connected_player_and_clears_when_empty():
    room = make_room(players=("ann", "bob", "cat"))
    room.remove_player("bob")
    assert room.host == "ann"  # a non-host leaving changes nothing
    room.remove_player("ann")
    assert room.host == "cat"
    room.remove_player("cat")
    assert room.host is None
    room.add_player("dan", FakeSocket())
    assert room.host == "dan"
