from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app import config
from app.game.graph.schemas import NonBlankStr

MAX_TOOL_CALLS = 6  # players wait in "generating" while the agent researches
# get_article is left out: full articles would flood the agent's context. The node fetches them.
# get_related_topics is left out: it returns the page's first links (near-alphabetical), not related ones.
AGENT_TOOLS = {"search_wikipedia", "get_summary"}

# Pinned so a server update can't change tool names or output shapes under us
wikipedia_mcp = MultiServerMCPClient({
    "wikipedia": {"transport": "stdio", "command": "uvx",
                  "args": ["wikipedia-mcp@2.0.1", "--enable-cache"]},
})


class ArticlePicks(BaseModel):
    titles: list[NonBlankStr] = Field(min_length=1, max_length=30,
                                      description="Exact Wikipedia article titles, as returned by search_wikipedia",
                                      examples=[["Amazon River", "Eiffel Tower"]])


system = """You pick Wikipedia articles that will supply source material for trivia questions.

Find {num_articles} articles for the given trivia category.

How to work:
1. First brainstorm specific subjects that a casual pub-quiz player has heard of and would enjoy
   being asked about (for a "Space" quiz: the Apollo 11 landing, Mars, the Hubble Space Telescope,
   not an obscure asteroid or a minor probe).
2. Then search for those subjects by name, in parallel, to get their exact article titles.

Rules:
- Each article is about one specific, well-known subject (a person, place, event, dish, brand, work...).
  Avoid broad overviews, lists, and disambiguation pages.
- Spread across the whole category; don't cluster around one theme.
- Never pick an article from the already-used list.
- Return exact titles as the tools give them."""

llm = ChatOpenAI(model="openai/gpt-6-luna", api_key=config.TOKEN_ROUTER_API_KEY,
                 base_url=config.BASE_URL, timeout=30, max_retries=1 , reasoning_effort="none")


def research_agent(tools: list[BaseTool], num_articles: int):
    return create_agent(
        llm,
        [t for t in tools if t.name in AGENT_TOOLS],
        system_prompt=system.format(num_articles=num_articles),
        response_format=ArticlePicks,
        # "continue": once over the limit, tool calls are refused and the model must answer
        middleware=[ToolCallLimitMiddleware(run_limit=MAX_TOOL_CALLS) ],
    )
