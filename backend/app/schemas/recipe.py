from pydantic import BaseModel

class RecipeCreate(BaseModel):
    name: str
    overlap: float
    wrap_style: str
    paper_id: int
    note: str = ""

class RecipeVersionIn(BaseModel):
    overlap: float
    wrap_style: str
    paper_id: int
    note: str = ""

class ActiveIn(BaseModel):
    active: bool
