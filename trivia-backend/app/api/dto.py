from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


class Category(StrEnum):
    GEOGRAPHY = "Geography"
    HISTORY = "History"
    SCIENCE_AND_NATURE = "Science and nature"
    SPORTS = "Sports"
    MOVIES_AND_TV = "Movies and TV"
    MUSIC = "Music"
    FOOD_AND_DRINK = "Food and drink"
    LITERATURE = "Literature"
    TECHNOLOGY = "Technology"
    ART_AND_CULTURE = "Art and culture"


# Free text: Category values are only suggestions for it
Topic = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]


class RoomCreate(BaseModel):
    room_name: str = Field(min_length=1, max_length=50, examples=["Friday Trivia"])
    room_description: str = Field(default="", max_length=200, examples=["This is room 1"])
    topic: Topic = Field(examples=["90s hip hop"])
    mode: Literal["trivia"] = "trivia"  # only game so far; new modes extend the Literal


class RoomOut(BaseModel):
    room_code: str
    room_name: str
    room_description: str
    topic: str
    mode: str
    phase: str
    players: list[str]
