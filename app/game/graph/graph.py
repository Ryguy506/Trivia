import asyncio
import random

from langgraph.graph import END, START, StateGraph

from app.game.graph.nodes import generate, plan_searches, should_continue, web_search
from app.game.graph.schemas import SourcedQuestion
from app.game.graph.state import GraphState

builder = StateGraph(GraphState)
builder.add_node("plan_searches", plan_searches)
builder.add_node("web_search", web_search)
builder.add_node("generate", generate)

builder.add_edge(START, "plan_searches")
builder.add_edge("plan_searches", "web_search")
builder.add_edge("web_search", "generate")
builder.add_conditional_edges("generate", should_continue, ["plan_searches", END])

trivia_graph = builder.compile()


async def generate_trivia(category: str, num_questions: int = 10) -> list[SourcedQuestion]:
    """Search the web for the category and return up to num_questions grounded questions."""
    state = await trivia_graph.ainvoke({
        "category": category,
        "num_questions": num_questions,
        "queries": [],
        "pending_queries": [],
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
