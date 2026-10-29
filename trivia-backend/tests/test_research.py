"""The research node with a fake Wikipedia MCP session and a fake agent: no network, no LLM."""
import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from app.game.graph import nodes
from app.game.graph.chains import judges
from app.game.graph.chains.research import ArticlePicks

LONG_TEXT = "The Eiffel Tower was completed in 1889. " * 20


class FakeSession:
    def __init__(self, articles):
        self.articles = articles  # title -> structuredContent dict, or an Exception to raise
        self.fetched = []

    async def call_tool(self, name, args):
        assert name == "get_article"
        self.fetched.append(args["title"])
        article = self.articles[args["title"]]
        if isinstance(article, Exception):
            raise article
        return SimpleNamespace(isError=False, structuredContent=article)


def article(title, text=LONG_TEXT):
    return {"title": title, "exists": True, "text": text, "url": f"https://en.wikipedia.org/wiki/{title}"}


def state(**overrides):
    return {"topic": "History", "difficulty": "medium", "num_questions": 10, "titles": [], "documents": [],
            "questions": [], "attempts": 0, **overrides}


def fake_wikipedia(monkeypatch, session, picks, difficulties=None):
    @asynccontextmanager
    async def open_session(name):
        yield session

    async def no_tools(session):
        return []

    class FakeAgent:
        async def ainvoke(self, _):
            return {"structured_response": ArticlePicks(titles=picks)}

    monkeypatch.setattr(nodes.wikipedia_mcp, "session", open_session)
    monkeypatch.setattr(nodes, "load_mcp_tools", no_tools)
    def make_agent(tools, n, difficulty):
        if difficulties is not None:
            difficulties.append(difficulty)
        return FakeAgent()

    monkeypatch.setattr(nodes, "research_agent", make_agent)
    monkeypatch.setattr(judges, "classifier", None)  # skip the Jev page check


def test_fetch_keeps_full_articles_and_skips_failures():
    session = FakeSession({
        "Eiffel Tower": article("Eiffel Tower", LONG_TEXT * 100),
        "Stub": article("Stub", "Too short."),
        "Missing": {"title": "Missing", "exists": False, "error": "Page does not exist"},
        "Broken": RuntimeError("server died"),
    })
    docs = asyncio.run(nodes._fetch_articles(session, ["Eiffel Tower", "Stub", "Missing", "Broken"]))
    assert [d["title"] for d in docs] == ["Eiffel Tower"]
    assert len(docs[0]["content"]) == nodes.MAX_CONTENT_CHARS
    assert docs[0]["url"] == "https://en.wikipedia.org/wiki/Eiffel Tower"


def test_research_skips_used_and_repeated_titles(monkeypatch):
    session = FakeSession({t: article(t) for t in ["Rome", "Carthage"]})
    fake_wikipedia(monkeypatch, session, ["Rome", "Sparta", "Carthage", "Rome"])
    out = asyncio.run(nodes.research(state(titles=["Sparta"], attempts=1)))
    assert session.fetched == ["Rome", "Carthage"]
    assert out["titles"] == ["Sparta", "Rome", "Carthage"]
    assert [d["title"] for d in out["documents"]] == ["Rome", "Carthage"]
    assert out["attempts"] == 2


def test_research_agent_gets_the_room_difficulty(monkeypatch):
    difficulties = []
    fake_wikipedia(monkeypatch, FakeSession({"Rome": article("Rome")}), ["Rome"], difficulties)
    asyncio.run(nodes.research(state(difficulty="hard")))
    assert difficulties == ["hard"]


def test_failed_round_counts_as_an_attempt_and_keeps_questions(monkeypatch):
    @asynccontextmanager
    async def broken_session(name):
        raise OSError("uvx not found")
        yield

    monkeypatch.setattr(nodes.wikipedia_mcp, "session", broken_session)
    out = asyncio.run(nodes.research(state(attempts=1)))
    assert out == {"attempts": 2, "documents": []}  # no "questions" key: earlier ones stay in state



def test_generate_writes_all_questions_in_one_call_and_maps_sources(monkeypatch):
    from app.game.graph.chains.generation import Generate, GeneratedQuestion

    calls = []

    def q(text, source):
        return GeneratedQuestion(question=text, options=["A", "B", "C", "D"], correct_index=0,
                                 supporting_quote="The answer is A.", source=source)

    class FakeChain:
        async def ainvoke(self, inputs):
            calls.append(inputs)
            return Generate(questions=[q("About Rome?", 0), q("About Carthage?", 1),
                                       q("About nothing?", 5), q("about  rome?", 0)])

    monkeypatch.setattr(nodes, "generation_chain", FakeChain())
    monkeypatch.setattr(judges, "classifier", None)
    docs = [{"url": "u/rome", "title": "Rome", "content": "x"}, {"url": "u/carthage", "title": "Carthage", "content": "y"}]
    out = asyncio.run(nodes.generate(state(documents=docs)))

    assert len(calls) == 1
    assert "[Source 0] Rome" in calls[0]["context"] and "[Source 1] Carthage" in calls[0]["context"]
    # out-of-range source dropped, near-duplicate dropped
    assert [(x.question, x.source_url) for x in out["questions"]] == [("About Rome?", "u/rome"),
                                                                      ("About Carthage?", "u/carthage")]


def test_failed_generation_keeps_earlier_questions(monkeypatch):
    class BrokenChain:
        async def ainvoke(self, inputs):
            raise RuntimeError("429")

    monkeypatch.setattr(nodes, "generation_chain", BrokenChain())
    docs = [{"url": "u", "title": "T", "content": "x"}]
    assert asyncio.run(nodes.generate(state(documents=docs))) == {}
