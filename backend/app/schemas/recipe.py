from typing import Literal

from pydantic import BaseModel, Field


class RecipeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    overlap: float = Field(gt=0)
    wrap_style: Literal["cross", "band"]
    paper_id: int


class RevisionCreate(BaseModel):
    overlap: float = Field(gt=0)
    wrap_style: Literal["cross", "band"]
    paper_id: int
