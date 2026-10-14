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

    def remove_player(self, player_name: str) -> None:
        self.connections.pop(player_name, None)

    def add_answer(self, player_name: str, answer: str) -> None:
        if self.current_question is None:
            return
        if player_name not in self.answers:
          self.answers[player_name] = answer

    def add_score(self, player_name: str) -> None:
        if player_name not in self.score:
            self.score[player_name] = 0
        if self.answers[player_name] == self.current_question.correct_index:
            self.score[player_name] += 1

    def reset_ansewers(self) -> None:
        self.answers = {}


    async def broadcast(self, message: dict) -> None:
        # Copy the items so a player leaving mid-loop doesn't break iteration
        for player_name, socket in list(self.connections.items()):
            try:
                await socket.send_json(message)
            except Exception:
                self.remove_player(player_name)

    
    async def change_phase(self, phase: str) -> None:
        self.phase = phase
        await self.broadcast({"type": "phase", "phase": phase})