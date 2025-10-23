from __future__ import annotations
from datetime import datetime
from uuid import uuid4
from typing import Any, Dict
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from SPTOVZ.database import get_db
from SPTOVZ.models.class_group import Key, Class
from SPTOVZ.models.session import TestSession
from SPTOVZ.models.testbank import TestContent
from SPTOVZ.schemas.session import StartTestRequest, StartTestResponse
from SPTOVZ.utils.test_selector import select_test
from SPTOVZ.utils.emspt_engine import compute_emspt, Profile

templates = Jinja2Templates(directory="SPTOVZ/templates")

router = APIRouter(prefix="/session", tags=["Session"])

def _norm(s: str) -> str:
    return (s or "").strip().lower()

@router.post("/start-test", response_model=StartTestResponse)
def start_test(payload: StartTestRequest, db: Session = Depends(get_db)) -> StartTestResponse:
    key: Key | None = db.query(Key).filter(Key.code == payload.code).first()
    if not key:
        raise HTTPException(status_code=404, detail="Неверный код доступа")
    if key.used:
        raise HTTPException(status_code=400, detail="Этот код уже использован")

    # Удаляем старую сессию, если есть
    old_session = db.query(TestSession).filter(TestSession.key_id == key.id).first()
    if old_session:
        old_session.answers = None
        old_session.result = None
        db.commit()

    cls: Class | None = db.get(Class, key.class_id)
    if not cls or not cls.education_type:
        raise HTTPException(status_code=400, detail="Класс/учреждение не определены")

    institution = cls.education_type                # school|college|university
    impairment = _norm(payload.diagnosis)           # hearing|vision|motor

    try:
        passport, content = select_test(db, institution=institution, impairment=impairment)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    session = TestSession(
        id=str(uuid4()),
        key_id=key.id,
        age=payload.age,              # ✅ исправлено
        gender=_norm(payload.gender), # ✅ исправлено
        diagnosis=impairment,
        form_type=key.form_type,
        test_name=passport.id,        # meta.code
        started_at=datetime.utcnow(),
        answers=None,
        result=None,
    )

    key.used = False  # пока тест не пройден
    db.add(session)
    db.commit()
    db.refresh(session)

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

    # --- Преобразуем ответы ---
    answers_map = {int(a["id"]): int(a["value"]) for a in answers_raw}

    session.answers = answers_map
    db.commit()

    content = db.query(TestContent).filter_by(id=session.test_name).first()
    if not content:
        raise HTTPException(status_code=500, detail=f"Контент теста '{session.test_name}' не найден")

    profile = Profile(
        form=session.form_type,
        impairment=session.diagnosis,
        gender=session.gender,
    )

    computed = compute_emspt(
        answers_map=answers_map,
        profile=profile,
    )

    session.result = computed

    key = db.query(Key).filter(Key.id == session.key_id).first()
    if key:
        key.used = True

    session.finished_at = datetime.utcnow()
    db.commit()

    return {
        "session_id": session.id,
        "saved": True,
        "questions": len(answers_map),
        "computed": True,
        "result": computed,
    }

import json

@router.get("/result/{session_id}", response_class=HTMLResponse)
def get_test_result(request: Request, session_id: str, db: Session = Depends(get_db)):
    session = db.get(TestSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    if not session.result:
        raise HTTPException(status_code=400, detail="Результаты ещё не рассчитаны")

    # 🔧 Распаковываем JSON, если это строка
    result = session.result
    if isinstance(result, str):
        result = json.loads(result)

    sten_data = result.get("sten", {})
    profile = result.get("profile", {})

    return templates.TemplateResponse(
        "result_page.html",
        {
            "request": request,
            "session_id": session_id,
            "sten_data": sten_data,
            "profile": profile,
            "irp": result.get("irp"),
            "irp_interval": result.get("irp_interval"),
            "kveripo": result.get("kveripo"),
            "kveripo_interval": result.get("kveripo_interval"),
        },
    )

