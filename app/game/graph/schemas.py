"""Models shared across the graph, chains and game. No side effects on import."""
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator

# Strips whitespace (incl. non-breaking spaces) so blank/padding-only output fails validation
NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class MultipleChoiceQuestion(BaseModel):
    question: NonBlankStr = Field(min_length=5, description="The question text",
                                  examples=["What is the capital of France?"])
    options: list[NonBlankStr] = Field(min_length=4, max_length=4,
                               description="Exactly 4 answer choices, one of which is correct",
                               examples=[["Paris", "Lyon", "Marseille", "Nice"]])
    correct_index: int = Field(ge=0, le=3, description="Index (0-3) of the correct option")
    supporting_quote: NonBlankStr = Field(min_length=5, description="Verbatim sentence from the context that proves the answer")

    @model_validator(mode="after")
    def options_are_unique(self):
        if len({o.strip().lower() for o in self.options}) != len(self.options):
            raise ValueError("options must be unique")
        return self


class SourcedQuestion(MultipleChoiceQuestion):
    source_url: str
