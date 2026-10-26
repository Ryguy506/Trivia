from typing import TypedDict

from app.game.graph.schemas import SourcedQuestion


class Document(TypedDict):
    url: str
    title: str
    content: str


class GraphState(TypedDict):
    category: str
    num_questions: int
    titles: list[str]             # every Wikipedia article picked so far, so retries find new ones
    documents: list[Document]     # articles from the current round
    questions: list[SourcedQuestion]
    attempts: int
