from pydantic import BaseModel
from typing import Optional, List, Any

# === Запрос на начало теста ===
class StartTestRequest(BaseModel):
    code: str
    age: int
    gender: str
    diagnosis: str
    # education_type — больше не нужен, он берётся через психолога

# === Ответ при старте теста ===
class StartTestResponse(BaseModel):
    session_id: str
    test_name: str
    form_type: str
    questions: List[str]  # Список вопросов

# === Сохранение результатов (будет позже) ===
class SubmitAnswersRequest(BaseModel):
    session_id: str
    answers: List[Any]
