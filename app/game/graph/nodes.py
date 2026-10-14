import asyncio
import logging
import math
import random

from dotenv import load_dotenv
from langchain_tavily import TavilySearch
from langgraph.graph import END

from app.game.graph.chains.categoryContext import search_plan_chain
from app.game.graph.chains.generation import generation_chain
from app.game.graph.chains import judges
from app.game.graph.schemas import MultipleChoiceQuestion, SourcedQuestion
from app.game.graph.state import Document, GraphState

load_dotenv()
logger = logging.getLogger(__name__)

BRAINSTORM_QUERIES = 20   # the LLM brainstorms this many; we randomly pick from them
QUERIES_PER_ROUND = 4
QUESTIONS_PER_DOC = 2
MIN_CONTENT_CHARS = 200   # skip snippets too short to ground a question
MAX_ATTEMPTS = 3
EXTRA_DOCS = 2            # pages kept beyond what's needed, as a buffer for rejected questions

# Jev thresholds (probabilities 0-1);
PAGE_USEFUL_MIN = 0.5
ANSWER_SUPPORTED_MIN = 0.8
ANSWER_AMBIGUOUS_MAX = 0.3

web_search_tool = TavilySearch(max_results=3, search_depth="advanced")


def _norm(text: str) -> str:
    return " ".join(text.split()).lower()


async def plan_searches(state: GraphState) -> dict:
    plan = await search_plan_chain.ainvoke({
        "category": state["category"],
        "num_queries": BRAINSTORM_QUERIES,
        "used_queries": "\n".join(state["queries"]) or "none",
    })
    # LLMs suggest similar topics every time; sampling randomly keeps each game different
    fresh = [q for q in plan.queries if q not in state["queries"]]
    picked = random.sample(fresh, min(QUERIES_PER_ROUND, len(fresh)))
    return {"pending_queries": picked, "queries": state["queries"] + picked,
            "attempts": state["attempts"] + 1}


async def web_search(state: GraphState) -> dict:
    responses = await asyncio.gather(
        *(web_search_tool.ainvoke({"query": q}) for q in state["pending_queries"]),
        return_exceptions=True,
    )
    used_urls = {q.source_url for q in state["questions"]}
    documents: list[Document] = []
    for response in responses:
        # Failed searches come back as an exception, an error string, or {"error": ...}
        if not isinstance(response, dict) or "results" not in response:
            continue
        for result in response["results"]:
            content = result.get("content") or ""
            if result["url"] in used_urls or len(content) < MIN_CONTENT_CHARS:
                continue
            used_urls.add(result["url"])
            documents.append({"url": result["url"], "title": result.get("title", ""), "content": content})

    needed = state["num_questions"] - len(state["questions"])
    max_docs = math.ceil(needed / QUESTIONS_PER_DOC) + EXTRA_DOCS
    return {"documents": await _best_pages(state["category"], documents, max_docs)}


async def _best_pages(category: str, documents: list[Document], max_docs: int) -> list[Document]:
    """Use Jev to drop weak pages and keep the most useful ones, before any LLM generation."""
    if judges.classifier is None or not documents:
        return documents[:max_docs]
    responses = await judges.classifier.abatch(
        [judges.page_request(category, d["title"], d["content"]) for d in documents],
        return_exceptions=True,
    )
    scored = []
    for doc, response in zip(documents, responses):
        if isinstance(response, Exception):
            logger.warning("Jev page check failed, keeping page: %s", response)
            usefulness = PAGE_USEFUL_MIN  # unknown: keep it, but rank it below confident pages
        else:
            usefulness = response.nouls[judges.USEFUL].noul
        if usefulness >= PAGE_USEFUL_MIN:
            scored.append((usefulness, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _, doc in scored[:max_docs]]


async def generate(state: GraphState) -> dict:
    documents = state["documents"]
    needed = state["num_questions"] - len(state["questions"])
    if not documents or needed <= 0:
        return {}

    per_doc = min(QUESTIONS_PER_DOC, math.ceil(needed / len(documents)))
    results = await generation_chain.abatch(
        [{"num_questions": per_doc, "context": doc["content"]} for doc in documents],
        return_exceptions=True,
    )

    candidates = [
        (doc, q)
        for doc, result in zip(documents, results) if not isinstance(result, Exception)
        for q in result.questions
    ]
    candidates = await _verified(candidates)

    seen = {_norm(q.question) for q in state["questions"]}
    new_questions: list[SourcedQuestion] = []
    for doc, q in candidates:
        if _norm(q.question) in seen:
            continue
        seen.add(_norm(q.question))
        new_questions.append(SourcedQuestion(**q.model_dump(), source_url=doc["url"]))
    return {"questions": state["questions"] + new_questions}


async def _verified(candidates: list[tuple[Document, MultipleChoiceQuestion]]):
    """Use Jev to keep only questions whose answer the source supports and that have one right option.

    This is the only correctness check, so a question Jev couldn't judge is dropped.
    """
    if not candidates:
        return candidates
    if judges.classifier is None:
        logger.warning("No Jev classifier configured: %d questions are unverified", len(candidates))
        return candidates
    responses = await judges.classifier.abatch(
        [judges.answer_request(doc["content"], q) for doc, q in candidates],
        return_exceptions=True,
    )
    kept = []
    for candidate, response in zip(candidates, responses):
        if isinstance(response, Exception):
            logger.warning("Jev answer check failed, dropping question: %s", response)
            continue
        nouls = response.nouls
        if (nouls[judges.SUPPORTED].noul >= ANSWER_SUPPORTED_MIN
                and nouls[judges.AMBIGUOUS].noul <= ANSWER_AMBIGUOUS_MAX):
            kept.append(candidate)
    return kept


def should_continue(state: GraphState) -> str:
    if len(state["questions"]) >= state["num_questions"] or state["attempts"] >= MAX_ATTEMPTS:
        return END
    return "plan_searches"
