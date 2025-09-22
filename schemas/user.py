from pydantic import BaseModel

# Схема регистрации пользователя (психолога)
class UserCreate(BaseModel):
    email: str
    password: str
    education_type: str  # Тип учреждения: школа, детсад, колледж и т.п.

# В будущем можно добавить схему отображения
class UserResponse(BaseModel):
    id: str
    email: str
    education_type: str

    class Config:
        orm_mode = True
