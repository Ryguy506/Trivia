import asyncio

import pytest

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


def test_round_end_sends_only_the_next_question():
    room = make_room()
    room.submit_answer("ann", 0)
    messages = room.submit_answer("bob", 1)
    # no scores and no correct answer between rounds
    assert messages == [{"type": "question", "index": 1, "total": 2,
                         "question": "Which letter is right?", "options": ["A", "B", "C", "D"],
                         "seconds": 30}]
    assert room.phase == "question"


def test_game_ends_after_last_question_is_answered():
    room = make_room(num_questions=2)
    for _ in range(2):
        room.submit_answer("ann", 0)
        messages = room.submit_answer("bob", 1)
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
    assert messages[-1] == {"type": "results", "scores": {"ann": 1, "bob": 0}}


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
    assert room.remove_player("cat") == [room.public_question()]
    assert room.current_index == 1


def test_player_who_left_keeps_their_score():
    room = make_room(num_questions=1)
    room.submit_answer("ann", 0)
    assert room.remove_player("ann") == []
    messages = room.submit_answer("bob", 1)
    assert messages[-1] == {"type": "results", "scores": {"ann": 1, "bob": 0}}


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
    assert ann.sent == [chat, room.public_question()]
    assert room.current_index == 1


def test_timer_ends_rounds_nobody_finished():
    room = make_room(num_questions=2)
    room.timer = 0.01
    room.submit_answer("ann", 0)  # bob never answers

    asyncio.run(room.run_timer())  # returns once the game reaches results

    assert room.phase == "results"
    bob = room.connections["bob"]
    assert [m["type"] for m in bob.sent] == ["question", "phase", "results"]
    assert bob.sent[-1]["scores"] == {"ann": 1, "bob": 0}


def test_finishing_early_restarts_the_timer_for_the_next_question():
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
