# SPTOVZ/routers/session.py
from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from SPTOVZ.database import get_db
from SPTOVZ.models.class_group import Key, Group, Class
from SPTOVZ.models.session import TestSession
from SPTOVZ.models.testbank import TestPassport, TestContent
from SPTOVZ.schemas.session import StartTestRequest, StartTestResponse
from SPTOVZ.utils.test_selector import select_test
from SPTOVZ.utils.emspt_engine import compute_emspt, Profile


router = APIRouter(prefix="/session", tags=["Session"])


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _normalize(s: str) -> str:
    return (s or "").strip().lower()


def _get_institution_from_key(db: Session, key: Key) -> str:
    """Получаем тип учреждения через Key → Group → Class."""
    group = db.get(Group, key.group_id) if key.group_id else None
    cls = group.class_ if group else (
        db.get(Class, key.class_id) if getattr(key, "class_id", None) else None
    )

    if not cls:
        raise HTTPException(status_code=400, detail="Ключ не привязан к классу/группе")

    if not hasattr(cls, "education_type") or not getattr(cls, "education_type"):
        raise HTTPException(
            status_code=500,
            detail="У класса отсутствует поле education_type (school|college|university)",
        )

    inst = _normalize(cls.education_type)
    if inst not in {"school", "college", "university"}:
        raise HTTPException(status_code=400, detail=f"Некорректный education_type='{inst}' у класса")
    return inst


# ---------------------------------------------------------------------
# /start-test
# ---------------------------------------------------------------------

@router.post("/start-test", response_model=StartTestResponse)
def start_test(payload: StartTestRequest, db: Session = Depends(get_db)) -> StartTestResponse:
    # 1) Проверяем ключ
    key: Key | None = db.query(Key).filter(Key.code == payload.code).first()
    if not key:
        raise HTTPException(status_code=404, detail="Неверный код доступа")
    if getattr(key, "used", False):
        raise HTTPException(status_code=400, detail="Этот код уже использован")

    # 2) Определяем параметры выбора теста
    institution = _get_institution_from_key(db, key)
    impairment = _normalize(payload.diagnosis)

    # 3) Выбираем тест
    try:
        passport, content = select_test(db, institution=institution, impairment=impairment)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 4) Создаём сессию теста
    session = TestSession(
        id=str(uuid4()),
        key_id=key.id,
        age=payload.age,
        gender=_normalize(payload.gender),
        diagnosis=impairment,
        form_type=passport.form,   # "A" | "B" | "C"
        test_name=passport.id,     # <-- важно: использовать meta.code, не title
        started_at=datetime.utcnow(),
        answers=None,
        result=None,
    )
    if hasattr(key, "used"):
        key.used = True

    db.add(session)
    db.commit()
    db.refresh(session)

    # 5) Отдаём клиенту информацию о тесте
    return StartTestResponse(
        session_id=session.id,
        test_name=passport.title,
        form_type=passport.form,
        questions=content.questions,
    )


# ---------------------------------------------------------------------
# /submit-answers
# ---------------------------------------------------------------------

@router.post("/submit-answers")
def submit_answers(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Принимает ответы участника и рассчитывает результат ЕМ СПТ.
    Формат:
    {
        "session_id": "...",
        "answers": [{"id": "1", "value": 3}, ...]
    }
    """
    session_id = payload.get("session_id")
    answers_raw = payload.get("answers")

    if not session_id or not answers_raw:
        raise HTTPException(status_code=400, detail="session_id и answers обязательны")

    session = db.get(TestSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    # --- Преобразуем ответы в словарь {id: value} ---
    if isinstance(answers_raw, list):
        if all(isinstance(x, dict) for x in answers_raw):
            answers_map = {str(a["id"]): int(a["value"]) for a in answers_raw}
        else:
            answers_map = {str(i + 1): int(v) for i, v in enumerate(answers_raw)}
    else:
        raise HTTPException(status_code=400, detail="Неверный формат answers")

    # --- Сохраняем ответы ---
    session.answers = answers_map
    db.commit()

    # --- Подгружаем контент теста ---
    content = db.get(TestContent, session.test_name)
    if not content:
        raise HTTPException(status_code=500, detail=f"Контент теста '{session.test_name}' не найден")

    # --- Формируем профиль участника ---
    profile = Profile(
        form=session.form_type,
        impairment=session.diagnosis,  # исправлено
        gender=session.gender,
    )

    # --- Расчёт результатов ---
    try:
        computed = compute_emspt(
            answers_map=answers_map,
            profile=profile,
            questions=content.questions,
            scoring_cfg=content.scoring,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка расчёта результатов: {e}")

    # --- Сохраняем результат ---
    session.result = computed
    db.commit()

    return {
        "session_id": session.id,
        "saved": True,
        "questions": len(answers_map),
        "computed": True,
        "result": computed,
    }
