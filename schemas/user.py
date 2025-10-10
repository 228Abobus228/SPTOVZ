from pydantic import BaseModel, EmailStr
from typing import Literal

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    institution_name: str
    education_type: Literal["school", "college", "university"]

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    institution_id: str
    class Config:
        orm_mode = True
