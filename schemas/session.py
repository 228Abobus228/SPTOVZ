from pydantic import BaseModel, Field
from typing import Any, List, Literal

class StartTestRequest(BaseModel):
    code: str
    age: int
    gender: str
    gender: Literal["male", "female"]
    diagnosis: Literal["hearing", "vision", "motor"]

class StartTestResponse(BaseModel):
    session_id: str
    test_name: str
    form_type: str
    questions: List[dict] = []

class AnswerItem(BaseModel):
    question_id: str
    value: int = Field(ge=1, le=10, description="Оценка 1..10")

class SubmitAnswersRequest(BaseModel):
    session_id: str
    answers: List[Any]