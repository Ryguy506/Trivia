from dataclasses import dataclass, field
from fastapi import WebSocket

from app.game.graph.schemas import SourcedQuestion


@dataclass
class Room:
    room_code: str
    room_name: str
    room_description: str
    category: str
    connections: dict[str, WebSocket] = field(default_factory=dict)
    phase: str = "lobby"
    questions: list[SourcedQuestion] = field(default_factory=list)
    current_index: int = 0
    answers: dict[str, int] = field(default_factory=dict)
    score: dict[str , int] = field(default_factory=dict)
    
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
                "question": q.question, "options": q.options}

    def player_names(self) -> list[str]:
        return list(self.connections.keys())

    def has_player(self, player_name: str) -> bool:
        return player_name in self.connections

    def add_player(self, player_name: str, player_socket: WebSocket) -> None:
        self.connections[player_name] = player_socket
        self.score.setdefault(player_name, 0)

    def remove_player(self, player_name: str) -> list[dict]:
        """Drop the player's connection (their score stays); returns the messages to broadcast."""
        if self.connections.pop(player_name, None) is None:
            return []
        # the round may have been waiting only on this player
        return self._end_round_if_done()

    def submit_answer(self, player_name: str, answer_index: object) -> list[dict]:
        """Record an answer; returns the messages to broadcast (empty until the round ends)."""
        if (self.phase != "question" or player_name not in self.connections
                or player_name in self.answers):
            return []
        # bool is an int subclass, so check the exact type of the client's value
        if type(answer_index) is not int or not 0 <= answer_index < len(self.current_question.options):
            return []
        self.answers[player_name] = answer_index
        return self._end_round_if_done()

    def _end_round_if_done(self) -> list[dict]:
        """Score the round once every connected player has answered, then advance or finish."""
        if self.phase != "question" or not self.connections or not self.connections.keys() <= self.answers.keys():
            return []
        correct_index = self.current_question.correct_index
        for player_name, answer_index in self.answers.items():
            if answer_index == correct_index:
                self.score[player_name] += 1
        self.answers = {}
        if self.next_question() is not None:
            return [self.public_question()]
        self.phase = "results"
        return [{"type": "phase", "phase": "results"},
                {"type": "results", "scores": dict(self.score)}]

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