from pydantic import BaseModel
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
    questions: List[str] = []

class SubmitAnswersRequest(BaseModel):
    session_id: str
    answers: List[Any]
