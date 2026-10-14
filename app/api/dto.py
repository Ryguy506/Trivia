from enum import StrEnum

from pydantic import BaseModel, Field


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


class RoomCreate(BaseModel):
    room_name: str = Field(min_length=1, max_length=50, examples=["Friday Trivia"])
    room_description: str = Field(default="", max_length=200, examples=["This is room 1"])
    category: Category = Field(examples=[Category.GEOGRAPHY])


class RoomOut(BaseModel):
    room_code: str
    room_name: str
    room_description: str
    category: Category
    phase: str
    players: list[str]
