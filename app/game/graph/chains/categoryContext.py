import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.game.graph.schemas import NonBlankStr

load_dotenv()


class SearchPlan(BaseModel):
    queries: list[NonBlankStr] = Field(min_length=1, max_length=30,
                                       description="Web search queries, each about a different specific subtopic",
                                       examples=[["Amazon River length and countries", "History of the Eiffel Tower"]])


system = """You plan web searches that will supply source material for trivia questions.

Given a trivia category, brainstorm {num_queries} web search queries.

Rules:
- Each query targets a different, specific subtopic of the category (a person, place, event, record, work, discovery...).
- Spread across the whole category; don't cluster around one theme.
- Mix famous and lesser-known subjects so the quiz has a range of difficulty.
- Prefer queries likely to return fact-rich pages (encyclopedias, histories, record lists).
- Don't repeat or closely paraphrase a previously used query."""

prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "Category: {category}\n\nPreviously used queries:\n{used_queries}"),
])

llm = ChatOpenAI(model="openai/gpt-6-luna", api_key=os.getenv("TOKEN_ROUTER_API_KEY"),
                 base_url=os.getenv("BASE_URL"), timeout=30, max_retries=1)

search_plan_chain = prompt | llm.with_structured_output(SearchPlan)
