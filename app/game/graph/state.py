from typing import TypedDict

from app.game.graph.schemas import SourcedQuestion


class Document(TypedDict):
    url: str
    title: str
    content: str


class GraphState(TypedDict):
    category: str
    num_questions: int
    queries: list[str]            # every query used so far, so retries search something new
    pending_queries: list[str]    # queries for the current search round
    documents: list[Document]     # search results from the current round
    questions: list[SourcedQuestion]
    attempts: int
