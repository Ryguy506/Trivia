import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, ValidationError, field_validator

from app import config
from app.game.graph.schemas import MultipleChoiceQuestion

logger = logging.getLogger(__name__)


class GeneratedQuestion(MultipleChoiceQuestion):
    source: int = Field(ge=0, description="Number of the [Source N] the question and quote come from")


class Generate(BaseModel):
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=50)

    @field_validator("questions", mode="before")
    @classmethod
    def drop_invalid(cls, questions):
        """One bad question (e.g. duplicate options) shouldn't throw away the whole batch."""
        if not isinstance(questions, list):
            return questions
        kept = []
        for q in questions:
            try:
                kept.append(GeneratedQuestion.model_validate(q))
            except ValidationError as e:
                logger.warning("Dropped invalid generated question: %s", e.errors()[0]["msg"])
        return kept


system = """You write multiple-choice trivia questions using ONLY the provided sources.

Rules:
- Each question has exactly 4 options and exactly one correct answer.
- The correct answer must be stated in the question's source; never use outside knowledge.
- Write at most {per_source} questions per source, spread across as many sources as you can.
- Set source to the number of the source the question comes from.
- Avoid questions whose answer is a date or year; they make dull trivia. Prefer who, what, where,
  why and how: people, places, names, records, causes, surprising facts. Ask at most one date
  question per 10, and only when the date itself is famous.
- Wrong options must be plausible and the same type as the answer (e.g. all cities, all people).
- Vary the position of the correct answer.
- supporting_quote must be copied word for word from that source.
- Don't reveal the answer in the question text.
- Difficulty: {difficulty}"""

# The room's level. Hard still needs exactly one supported answer: Jev drops ambiguous questions.
DIFFICULTY = {
    "easy": """easy. Ask about the most famous, headline facts of each source (what or who it is,
  where, what it's known for). Make the wrong options clearly different from the answer.""",
    "medium": """medium. Ask about notable facts a casual quiz player might know or could reason out.""",
    "hard": """hard. Ask about specific details from deeper in each source (numbers, records,
  lesser-known people or places). Make the wrong options close to the answer (similar names,
  nearby figures), but the source must still support only the correct one.""",
}

prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "Write {num_questions} questions from these sources:\n\n{context}"),
])


llm = ChatOpenAI(model="openai/gpt-6-luna", api_key=config.TOKEN_ROUTER_API_KEY,
                 base_url=config.BASE_URL, timeout=60, max_retries=1)

generation_chain = prompt | llm.with_structured_output(Generate)
