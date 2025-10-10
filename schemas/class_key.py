from pydantic import BaseModel
from typing import List, Literal

class ClassCreate(BaseModel):
    name: str

class ClassOut(BaseModel):
    id: str
    name: str
    education_type: Literal["school", "college", "university"]
    class Config:
        from_attributes = True

class KeyGenerateRequest(BaseModel):
    class_id: str
    count: int = 1

class KeyOut(BaseModel):
    code: str
    used: bool
    form_type: Literal["A", "B", "C"]
    education_type: Literal["school", "college", "university"]
    class Config:
        from_attributes = True
