from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from database import get_db
from models.class_group import Key, Group, Class
from models.session import TestSession
from models.user import User
from schemas.session import StartTestRequest, StartTestResponse
from tests.logic import determine_test_form
from tests import form_a, form_b, form_c

router = APIRouter(prefix="/session", tags=["test sessions"])

# === Начало теста ===
@router.post("/start", response_model=StartTestResponse)
def start_test(data: StartTestRequest, db: Session = Depends(get_db)):
    key = db.query(Key).filter(Key.code == data.code).first()
    if not key:
        raise HTTPException(status_code=404, detail="Invalid key")
    if key.used:
        raise HTTPException(status_code=400, detail="Key already used")

    group = db.query(Group).filter(Group.id == key.group_id).first()
    cls = db.query(Class).filter(Class.id == group.class_id).first()
    psychologist = db.query(User).filter(User.id == cls.psychologist_id).first()

    if not psychologist:
        raise HTTPException(status_code=500, detail="Psychologist not found")

    # Выбор теста и формы (по данным ребёнка + психолога)
    form_type, test_name = determine_test_form(
        age=data.age,
        gender=data.gender,
        diagnosis=data.diagnosis,
        education_type=psychologist.education_type
    )

    # Загрузка вопросов
    if form_type == "A":
        questions = form_a.questions
    elif form_type == "B":
        questions = form_b.questions
    elif form_type == "C":
        questions = form_c.questions
    else:
        raise HTTPException(status_code=500, detail="Unknown form type")

    # Создание сессии
    session = TestSession(
        id=str(uuid4()),
        key_id=key.id,
        age=data.age,
        gender=data.gender,
        diagnosis=data.diagnosis,
        form_type=form_type,
        test_name=test_name,
        started_at=datetime.utcnow()
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return StartTestResponse(
        session_id=session.id,
        test_name=test_name,
        form_type=form_type,
        questions=questions
    )
