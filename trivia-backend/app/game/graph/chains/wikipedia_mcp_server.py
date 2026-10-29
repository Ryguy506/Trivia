"""Runs wikipedia-mcp with our own User-Agent.

Wikipedia rate-limits (HTTP 429) the server's shared default User-Agent, and the server then reports
"no_results" for every search. 2.0.1 has no option for the UA, so we pin it on the class: the
property ignores the server's own assignment in __init__.
"""
# wikipedia_mcp is installed only in uvx's environment (research.py runs this file there), not the project's
# pyright: reportMissingImports=false
from wikipedia_mcp.__main__ import main
from wikipedia_mcp.wikipedia_client import WikipediaClient

# Wikipedia's UA policy asks for a contact (URL or email) in the UA
USER_AGENT = "TriviaGame/0.1 (https://github.com/Ryguy506/Trivia)"

WikipediaClient.user_agent = property(lambda self: USER_AGENT, lambda self, value: None)

if __name__ == "__main__":
    main()
