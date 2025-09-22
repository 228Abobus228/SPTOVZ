from pydantic import BaseModel

# === Класс ===
class ClassCreate(BaseModel):
    name: str

class ClassResponse(BaseModel):
    id: str
    name: str

    class Config:
        orm_mode = True

# === Группа ===
class GroupCreate(BaseModel):
    name: str
    class_id: str

class GroupResponse(BaseModel):
    id: str
    name: str
    class_id: str

    class Config:
        orm_mode = True

# === Ключ ===
class KeyResponse(BaseModel):
    id: str
    code: str
