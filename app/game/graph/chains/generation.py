import os
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.game.graph.schemas import MultipleChoiceQuestion

load_dotenv()


class Generate(BaseModel):
    questions: list[MultipleChoiceQuestion] = Field(min_length=1, max_length=50)


system = """You write multiple-choice trivia questions using ONLY the provided context.

Rules:
- Each question has exactly 4 options and exactly one correct answer.
- The correct answer must be stated in the context; never use outside knowledge.
- Wrong options must be plausible and the same type as the answer (e.g. all cities, all years).
- Vary the position of the correct answer.
- supporting_quote must be copied word for word from the context.
- Don't reveal the answer in the question text."""

prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "Write {num_questions} questions from this context:\n\n{context}"),
])

# gpt-oss-120b on TokenRouter took >30s per call; flash-lite is a fast non-reasoning model
llm = ChatOpenAI(model="openai/gpt-6-luna", api_key=os.getenv("TOKEN_ROUTER_API_KEY"),
                 base_url=os.getenv("BASE_URL"), timeout=30, max_retries=1)

generation_chain = prompt | llm.with_structured_output(Generate)
