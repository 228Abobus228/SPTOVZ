from __future__ import annotations
from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from SPTOVZ.database import get_db
from SPTOVZ.models.class_group import Key, Class
from SPTOVZ.models.session import TestSession
from SPTOVZ.models.testbank import TestContent
from SPTOVZ.schemas.session import StartTestRequest, StartTestResponse
from SPTOVZ.utils.test_selector import select_test
from SPTOVZ.utils.emspt_engine import compute_emspt, Profile

router = APIRouter(prefix="/session", tags=["Session"])

def _norm(s: str) -> str:
    return (s or "").strip().lower()

@router.post("/start-test", response_model=StartTestResponse)
def start_test(payload: StartTestRequest, db: Session = Depends(get_db)) -> StartTestResponse:
    # 1️⃣ Проверяем наличие кода
    key: Key | None = db.query(Key).filter(Key.code == payload.code).first()
    if not key:
        raise HTTPException(status_code=404, detail="Неверный код доступа")

    # 2️⃣ Проверяем — если тест уже был завершён
    if key.used:
        raise HTTPException(status_code=400, detail="Этот тест уже пройден.")

    # 3️⃣ Если ранее тест начинался, но не завершён — очистим старые данные
    old_session = db.query(TestSession).filter(TestSession.key_id == key.id).first()
    if old_session:
        old_session.answers = None
        old_session.result = None
        db.commit()

    # 4️⃣ Проверяем класс и тип учреждения
    cls: Class | None = db.get(Class, key.class_id)
    if not cls or not cls.education_type:
        raise HTTPException(status_code=400, detail="Класс/учреждение не определены")

    institution = cls.education_type  # school|college|university
    impairment = _norm(payload.diagnosis)  # hearing|vision|motor

    # 5️⃣ Подбираем тест
    try:
        passport, content = select_test(db, institution=institution, impairment=impairment)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 6️⃣ Создаём новую сессию
    session = TestSession(
        id=str(uuid4()),
        key_id=key.id,
        age=payload.age,
        gender=_norm(payload.gender),
        diagnosis=impairment,
        form_type=key.form_type,
        test_name=passport.id,
        started_at=datetime.utcnow(),
        answers=None,
        result=None,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    # 7️⃣ Возвращаем данные теста
    return StartTestResponse(
        session_id=session.id,
        test_name=passport.title,
        form_type=key.form_type,
        questions=content.questions,
    )


@router.post("/submit-answers")
def submit_answers(payload: Dict[str, Any], db: Session = Depends(get_db)):
    session_id = payload.get("session_id")
    answers_raw = payload.get("answers")
    if not session_id or not answers_raw:
        raise HTTPException(status_code=400, detail="session_id и answers обязательны")

    session = db.get(TestSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    if isinstance(answers_raw, list) and all(isinstance(x, dict) for x in answers_raw):
        answers_map = {str(a["id"]): int(a["value"]) for a in answers_raw}
    elif isinstance(answers_raw, list):
        answers_map = {str(i + 1): int(v) for i, v in enumerate(answers_raw)}
    else:
        raise HTTPException(status_code=400, detail="Неверный формат answers")

    session.answers = answers_map
    db.commit()

    content = db.get(TestContent, session.test_name)
    if not content:
        raise HTTPException(status_code=500, detail=f"Контент теста '{session.test_name}' не найден")

    profile = Profile(form=session.form_type, impairment=session.diagnosis, gender=session.gender)

    computed = compute_emspt(
        answers_map=answers_map,
        profile=profile,
        questions=content.questions,
        scoring_cfg=content.scoring,
    )

    session.result = computed
    key = db.query(Key).filter(Key.id == session.key_id).first()
    if key:
        key.used = True
    db.commit()

    return {
        "session_id": session.id,
        "saved": True,
        "questions": len(answers_map),
        "computed": True,
        "result": computed,
    }
