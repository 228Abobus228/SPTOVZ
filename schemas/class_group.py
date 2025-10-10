from pydantic import BaseModel
from typing import Literal

class ClassCreate(BaseModel):
    name: str
    psychologist_id: str
    education_type: Literal["school", "college", "university"]

class ClassOut(BaseModel):
    id: str
    name: str
    psychologist_id: str
    class Config:
        from_attributes = True

class GroupCreate(BaseModel):
    name: str
    class_id: str

class GroupOut(BaseModel):
    id: str
    name: str
    class_id: str
    class Config:
        from_attributes = True

class GenerateKeysRequest(BaseModel):
    count: int = 1

class KeyOut(BaseModel):
    id: str
    code: str
    used: bool
    group_id: str
    class Config:
        from_attributes = True
