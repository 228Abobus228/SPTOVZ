from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from database import get_db
from models.class_group import Key
from models.session import TestSession
from schemas.session import StartTestRequest, StartTestResponse

router = APIRouter(prefix="", tags=["testing"])

def pick_form(age: int, gender: str, diagnosis: str | None, education_type: str | None) -> tuple[str, str]:
    # TODO: подключить реальную логику выбора формы/теста
    # на первое время — единая заглушка
    return "A", "EAR"

@router.post("/start-test", response_model=StartTestResponse)
def start_test(payload: StartTestRequest, db: Session = Depends(get_db)):
    key = db.query(Key).filter(Key.code == payload.code).first()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    if key.used:
        raise HTTPException(status_code=400, detail="Key already used")

    # education_type вытаскиваем через key -> group -> class -> psychologist
    education_type = None
    if key.group and key.group.class_ and key.group.class_.psychologist:
        education_type = key.group.class_.psychologist.education_type

    form_type, test_name = pick_form(payload.age, payload.gender, payload.diagnosis, education_type)

    session = TestSession(
        id=str(uuid4()),
        key_id=key.id,
        age=payload.age,
        gender=payload.gender,
        diagnosis=payload.diagnosis,
        form_type=form_type,
        test_name=test_name,
        started_at=datetime.utcnow(),
    )
    key.used = True
    db.add(session)
    db.commit()
    db.refresh(session)

    # TODO: подставить реальные вопросы по выбранному тесту
    return StartTestResponse(
        session_id=session.id,
        test_name=test_name,
        form_type=form_type,
        questions=[]
    )
