import asyncio
import random

from langgraph.graph import END, START, StateGraph

from app.game.graph.nodes import generate, research, should_continue
from app.game.graph.schemas import SourcedQuestion
from app.game.graph.state import GraphState

builder = StateGraph(GraphState)
builder.add_node("research", research)
builder.add_node("generate", generate)

builder.add_edge(START, "research")
builder.add_edge("research", "generate")
builder.add_conditional_edges("generate", should_continue, ["research", END])

trivia_graph = builder.compile()


async def generate_trivia(topic: str, num_questions: int = 10) -> list[SourcedQuestion]:
    """Research Wikipedia for the topic and return up to num_questions grounded questions."""
    state = await trivia_graph.ainvoke({
        "topic": topic,
        "num_questions": num_questions,
        "titles": [],
        "documents": [],
        "questions": [],
        "attempts": 0,
    })
    questions = state["questions"]
    random.shuffle(questions)  # don't serve questions grouped by source
    return questions[:num_questions]


async def main():
    questions = await generate_trivia("History", num_questions=5)
    for q in questions:
        print(q.question)
        for i, option in enumerate(q.options):
            print(f"  {'*' if i == q.correct_index else ' '} {option}")
        print(f"  source: {q.source_url}\n")


if __name__ == "__main__":
    asyncio.run(main())
