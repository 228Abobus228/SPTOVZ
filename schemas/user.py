from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password: str
    education_type: str | None = None

class UserResponse(BaseModel):
    id: str
    email: str
    education_type: str | None = None

    class Config:
        from_attributes = True  # Pydantic v2
