import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app import config
from app.game.graph.schemas import MultipleChoiceQuestion


class GeneratedQuestion(MultipleChoiceQuestion):
    source: int = Field(ge=0, description="Number of the [Source N] the question and quote come from")


class Generate(BaseModel):
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=50)


system = """You write multiple-choice trivia questions using ONLY the provided sources.

Rules:
- Each question has exactly 4 options and exactly one correct answer.
- The correct answer must be stated in the question's source; never use outside knowledge.
- Write at most {per_source} questions per source, spread across as many sources as you can.
- Set source to the number of the source the question comes from.
- Wrong options must be plausible and the same type as the answer (e.g. all cities, all years).
- Vary the position of the correct answer.
- supporting_quote must be copied word for word from that source.
- Don't reveal the answer in the question text."""

prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "Write {num_questions} questions from these sources:\n\n{context}"),
])

# gpt-oss-120b on TokenRouter took >30s per call; flash-lite is a fast non-reasoning model.
# timeout 60: one call writes the whole round's questions from all sources
llm = ChatOpenAI(model="openai/gpt-6-luna", api_key=config.TOKEN_ROUTER_API_KEY,
                 base_url=config.BASE_URL, timeout=60, max_retries=1)

generation_chain = prompt | llm.with_structured_output(Generate)
