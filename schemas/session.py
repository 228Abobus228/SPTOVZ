from pydantic import BaseModel
from typing import Any, List, Literal

class StartTestRequest(BaseModel):
    code: str
    age: int
    gender: str
    # allowed: 'hearing' | 'vision' | 'motor'
    diagnosis: Literal["hearing", "vision", "motor"] = Field(..., description="Форма нарушения")

class StartTestResponse(BaseModel):
    session_id: str
    test_name: str
    form_type: str
    questions: List[str] = []

class SubmitAnswersRequest(BaseModel):
    session_id: str
    answers: List[Any]
