from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from SPTOVZ.database import get_db
from SPTOVZ.models.class_group import Key
from SPTOVZ.models.session import TestSession
from SPTOVZ.models.testbank import TestPassport, TestContent
from SPTOVZ.schemas.session import StartTestRequest, StartTestResponse, SubmitAnswersRequest
from SPTOVZ.utils.test_selector import select_test_code
from SPTOVZ.utils.scoring import compute_result

router = APIRouter(prefix="", tags=["testing"])

@router.post("/start-test", response_model=StartTestResponse)
def start_test(payload: StartTestRequest, db: Session = Depends(get_db)):
    key = db.query(Key).filter(Key.code == payload.code).first()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    if key.used:
        raise HTTPException(status_code=400, detail="Key already used")

    # тип учреждения из пользователя-психолога
    education_type = None
    if key.group and key.group.class_ and key.group.class_.psychologist:
        education_type = key.group.class_.psychologist.education_type

    if not education_type:
        raise HTTPException(status_code=400, detail="У психолога не задан тип учреждения")

    try:
        test_code = select_test_code(education_type, payload.diagnosis, payload.gender)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    passport = db.get(TestPassport, test_code)
    content = db.get(TestContent, test_code)
    if not passport or not content:
        raise HTTPException(status_code=500, detail=f"Тест {test_code} не найден. Импортируй каталог тестов.")

    session = TestSession(
        id=str(uuid4()),
        key_id=key.id,
        age=payload.age,
        gender=payload.gender,
        diagnosis=payload.diagnosis,
        form_type=str(passport.version),   # можешь хранить тут код формы, если нужно
        test_name=passport.title,
        started_at=datetime.utcnow(),
    )
    key.used = True
    db.add(session)
    db.commit()
    db.refresh(session)

    return StartTestResponse(
        session_id=session.id,
        test_name=passport.title,
        form_type=str(passport.version),
        questions=content.questions,
    )

@router.post("/submit-answers")
def submit_answers(payload: SubmitAnswersRequest, db: Session = Depends(get_db)):
    session = db.query(TestSession).get(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.finished_at:
        raise HTTPException(status_code=400, detail="Session already finished")

    # Определяем какой тест проходил пользователь (по тем же правилам)
    key = session.key
    education_type = None
    if key and key.group and key.group.class_ and key.group.class_.psychologist:
        education_type = key.group.class_.psychologist.education_type
    if not education_type:
        raise HTTPException(status_code=400, detail="У психолога не задан тип учреждения")

    test_code = select_test_code(education_type, session.diagnosis, session.gender)
    passport = db.get(TestPassport, test_code)
    content = db.get(TestContent, test_code)
    if not passport or not content:
        raise HTTPException(status_code=500, detail=f"Тест {test_code} не найден. Импортируй каталог тестов.")

    answers_dict = {a.question_id: a.value for a in payload.answers}

    try:
        result = compute_result(answers_dict, content.questions, content.scoring)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    session.answers = answers_dict
    session.result = result
    session.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(session)

    return {"session_id": session.id, "result": result}