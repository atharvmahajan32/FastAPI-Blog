from typing import Optional
from pydantic import BaseModel

class PostCreate(BaseModel):
    title: str
    content: str

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class ReasonCreate(BaseModel):
    name: str
    why: str