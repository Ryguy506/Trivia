import asyncio
from dataclasses import dataclass, field
from fastapi import WebSocket

from app.game.graph.schemas import SourcedQuestion

REVEAL_SECONDS = 4  # how long the answer shows before the next question


@dataclass
class Room:
    room_code: str
    room_name: str
    room_description: str
    topic: str
    mode: str
    difficulty: str = "medium"
    connections: dict[str, WebSocket] = field(default_factory=dict)
    phase: str = "lobby"
    questions: list[SourcedQuestion] = field(default_factory=list)
    current_index: int = 0
    answers: dict[str, int] = field(default_factory=dict)
    score: dict[str , int] = field(default_factory=dict)
    host: str | None = None
    timer: float = 30  # seconds per question
    # set by _end_round: run_timer then shows the answer and moves on; while set, answers are ignored
    round_ended: asyncio.Event = field(default_factory=asyncio.Event)
    timer_task: asyncio.Task | None = None  # held here so the running task isn't garbage-collected
    questions_task: asyncio.Task | None = None

    def prepare_questions(self, question_source) -> None:
        """Generate in the background from room creation, so Start rarely waits the full ~30 s."""
        self.questions_task = asyncio.create_task(question_source(self.topic, self.difficulty))

    async def run_timer(self) -> None:
        """Runs once per game: ends any round still open after `timer` seconds, leaves the answer
        up for REVEAL_SECONDS, then sends the next question, until results."""
        while self.phase == "question":
            self.round_ended.clear()
            try:
                await asyncio.wait_for(self.round_ended.wait(), self.timer)
            except TimeoutError:
                for message in self._end_round():
                    await self.broadcast(message)
            await asyncio.sleep(REVEAL_SECONDS)
            for message in self.advance():
                await self.broadcast(message)

    @property
    def current_question(self) -> SourcedQuestion | None:
        if 0 <= self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def set_questions(self, questions: list[SourcedQuestion]) -> None:
        self.questions = questions
        self.current_index = 0

    def next_question(self) -> SourcedQuestion | None:
        """Advance to the next question; returns None when the game is out of questions."""
        self.current_index += 1
        return self.current_question

    def public_question(self) -> dict | None:
        """The current question as players may see it: no answer, quote or source."""
        q = self.current_question
        if q is None:
            return None
        return {"type": "question", "index": self.current_index, "total": len(self.questions),
                "question": q.question, "options": q.options, "seconds": self.timer}

    def player_names(self) -> list[str]:
        return list(self.connections.keys())

    def has_player(self, player_name: str) -> bool:
        return player_name in self.connections

    def add_player(self, player_name: str, player_socket: WebSocket) -> None:
        self.connections[player_name] = player_socket
        self.score.setdefault(player_name, 0)
        if self.host is None:
            self.host = player_name

    def remove_player(self, player_name: str) -> list[dict]:
        """Drop the player's connection (their score stays); returns the messages to broadcast."""
        if self.connections.pop(player_name, None) is None:
            return []
        if self.host == player_name:
            # connections keep join order, so this is the longest-connected player (None if empty)
            self.host = next(iter(self.connections), None)
        # the round may have been waiting only on this player
        return self._end_round_if_done()

    def submit_answer(self, player_name: str, answer_index: object) -> list[dict]:
        """Record an answer; returns the messages to broadcast (empty until the round ends)."""
        if (self.phase != "question" or self.round_ended.is_set() or player_name not in self.connections
                or player_name in self.answers):
            return []
        # bool is an int subclass, so check the exact type of the client's value
        if type(answer_index) is not int or not 0 <= answer_index < len(self.current_question.options):
            return []
        self.answers[player_name] = answer_index
        return self._end_round_if_done()

    def _end_round(self) -> list[dict]:
        """Score the round (no answer counts as wrong) and reveal the answer; run_timer moves on."""
        self.round_ended.set()
        q = self.current_question
        for player_name, answer_index in self.answers.items():
            if answer_index == q.correct_index:
                self.score[player_name] += 1
        self.answers = {}
        # each client compares correct_index with its own pick, so no one's pick is sent
        return [{"type": "round_result", "index": self.current_index, "correct_index": q.correct_index,
                 "supporting_quote": q.supporting_quote, "source_url": q.source_url,
                 "scores": dict(self.score)}]

    def advance(self) -> list[dict]:
        """After the reveal: the next question, or the results after the last one."""
        if self.next_question() is not None:
            return [self.public_question()]
        self.phase = "results"
        return [{"type": "phase", "phase": "results"},
                {"type": "results", "scores": dict(self.score)}]

    def _end_round_if_done(self) -> list[dict]:
        """End the round once every connected player has answered."""
        if self.phase != "question" or not self.connections or not self.connections.keys() <= self.answers.keys():
            return []
        return self._end_round()

    async def broadcast(self, message: dict) -> None:
        # Copy the items so a player leaving mid-loop doesn't break iteration
        follow_ups = []
        for player_name, socket in list(self.connections.items()):
            try:
                await socket.send_json(message)
            except Exception:
                follow_ups += self.remove_player(player_name)
        # sent after the loop so everyone gets this message before the next one
        for follow_up in follow_ups:
            await self.broadcast(follow_up)

    
    async def change_phase(self, phase: str) -> None:
        self.phase = phase
        await self.broadcast({"type": "phase", "phase": phase})