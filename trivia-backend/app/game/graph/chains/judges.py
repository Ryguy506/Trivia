"""Fast yes/no judgments with TypeSafe's Jev classifier (no text generation).

Jev returns a calibrated probability per question, so callers pick thresholds.
"""

from langchain_typesafe import ClassifierRequest, Noul, NoulCriteria, TypeSafeClassifier

from app import config
from app.game.graph.schemas import MultipleChoiceQuestion

class TokenRouterClassifier(TypeSafeClassifier):
    """TypeSafeClassifier pointed at TokenRouter's Jev endpoint.

    The library always posts to `{base_url}/v1/systemone`, which TokenRouter doesn't serve (404);
    TokenRouter's endpoint is `/api/alpha/decisions` with the same request body. `_endpoint` is a
    private hook of langchain-typesafe 0.0.1a3 (pinned), so recheck this if you upgrade.
    """

    @property
    def _endpoint(self) -> str:
        return self.base_url


# Creating the classifier fails without a key, so it's optional: None means "skip these checks"
classifier = TokenRouterClassifier(
    api_key=config.TOKEN_ROUTER_API_KEY,
    base_url="https://api.tokenrouter.com/api/alpha/decisions",
    model="typesafe/jev-1.13",  # TokenRouter has no "jev-latest" (the library default)
) if config.TOKEN_ROUTER_API_KEY else None

USEFUL = "useful"
SUPPORTED = "supported"
AMBIGUOUS = "ambiguous"


def page_request(topic: str, title: str, content: str) -> ClassifierRequest:
    return {
        "state": {"trivia_topic": topic, "page_title": title, "page_text": content},
        "questions": {
            USEFUL: Noul(
                instructions="Is this page text a good source for trivia questions on the given topic?",
                criteria=NoulCriteria(
                    true="About the topic and states specific, checkable facts (names, dates, numbers, places).",
                    false="Off-topic, mostly opinion or marketing, navigation/boilerplate, or too vague to quiz on.",
                ),
            ),
        },
    }


def answer_request(content: str, question: MultipleChoiceQuestion) -> ClassifierRequest:
    return {
        "state": {
            "source_text": content,
            "question": question.question,
            "options": question.options,
            "proposed_correct_answer": question.options[question.correct_index],
        },
        "questions": {
            SUPPORTED: Noul(
                instructions="Does the source text clearly support the proposed correct answer to the question?"
            ),
            AMBIGUOUS: Noul(
                instructions="Based on the source text, could any option other than the proposed one also be a correct answer?"
            ),
        },
    }
