import asyncio
import logging
import math

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.graph import END

from app.game.graph.chains.research import research_agent, wikipedia_mcp
from app.game.graph.chains.generation import generation_chain
from app.game.graph.chains import judges
from app.game.graph.schemas import MultipleChoiceQuestion, SourcedQuestion
from app.game.graph.state import Document, GraphState

logger = logging.getLogger(__name__)

QUESTIONS_PER_DOC = 2
MIN_CONTENT_CHARS = 200   # skip stubs too short to ground a question
MAX_CONTENT_CHARS = 8000  # the article's opening is enough for 2 questions and keeps LLM/Jev input small
MAX_ATTEMPTS = 3
EXTRA_DOCS = 2            # pages kept beyond what's needed, as a buffer for rejected questions
EXTRA_PICKS = 2           # articles the agent picks beyond max_docs, so Jev has some to reject

# Jev thresholds (probabilities 0-1);
PAGE_USEFUL_MIN = 0.5
ANSWER_SUPPORTED_MIN = 0.8
ANSWER_AMBIGUOUS_MAX = 0.3


def _norm(text: str) -> str:
    return " ".join(text.split()).lower()


async def research(state: GraphState) -> dict:
    """An agent browses Wikipedia (over MCP) to pick articles; then we fetch their full text."""
    needed = state["num_questions"] - len(state["questions"])
    max_docs = math.ceil(needed / QUESTIONS_PER_DOC) + EXTRA_DOCS
    # shortcut: starts a Wikipedia MCP server per round (a few seconds); keep one alive for the
    # app's lifetime if that shows up in the "generating" wait.
    try:
        async with wikipedia_mcp.session("wikipedia") as session:
            agent = research_agent(await load_mcp_tools(session), max_docs + EXTRA_PICKS, state["difficulty"])
            used = "\n".join(state["titles"]) or "none"
            result = await agent.ainvoke({"messages": [{"role": "user", "content":
                                          f"Topic: {state['topic']}\n\nAlready used:\n{used}"}]})
            titles = list(dict.fromkeys(t for t in result["structured_response"].titles
                                        if t not in state["titles"]))
            documents = await _fetch_articles(session, titles)
    except Exception:
        # A failed round counts as an attempt; questions from earlier rounds are kept
        logger.exception("Research round failed")
        return {"attempts": state["attempts"] + 1, "documents": []}
    return {"titles": state["titles"] + titles, "attempts": state["attempts"] + 1,
            "documents": await _best_pages(state["topic"], documents, max_docs)}


async def _fetch_articles(session, titles: list[str]) -> list[Document]:
    """Full article text, so questions and Jev checks are grounded in the real page, not a summary."""
    results = await asyncio.gather(*(session.call_tool("get_article", {"title": t}) for t in titles),
                                   return_exceptions=True)
    documents: list[Document] = []
    for title, result in zip(titles, results):
        # Failures come back as an exception, an MCP error result, or {"exists": false}
        article = None if isinstance(result, Exception) or result.isError else result.structuredContent
        if not article or not article.get("exists"):
            logger.warning("Couldn't fetch article %r: %s", title, result)
            continue
        content = (article.get("text") or "")[:MAX_CONTENT_CHARS]
        if len(content) >= MIN_CONTENT_CHARS:
            documents.append({"url": article.get("url") or title, "title": article["title"], "content": content})
    return documents


async def _best_pages(topic: str, documents: list[Document], max_docs: int) -> list[Document]:
    """Use Jev to drop weak pages and keep the most useful ones, before any LLM generation."""
    if judges.classifier is None or not documents:
        return documents[:max_docs]
    responses = await judges.classifier.abatch(
        [judges.page_request(topic, d["title"], d["content"]) for d in documents],
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
    # One call for all pages: TokenRouter allows only 10 requests a minute
    context = "\n\n".join(f"[Source {i}] {doc['title']}\n{doc['content']}" for i, doc in enumerate(documents))
    try:
        result = await generation_chain.ainvoke({"num_questions": per_doc * len(documents),
                                                 "per_source": per_doc, "context": context})
    except Exception:
        logger.exception("Question generation failed")  # the round counts as an attempt
        return {}

    candidates = [(documents[q.source], MultipleChoiceQuestion(**q.model_dump(exclude={"source"})))
                  for q in result.questions if q.source < len(documents)]
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
    return "research"
