# SPTOVZ/routers/session.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from SPTOVZ.database import get_db
from SPTOVZ.models.class_group import Key, Group, Class
from SPTOVZ.models.session import TestSession
from SPTOVZ.models.testbank import TestPassport, TestContent
from SPTOVZ.schemas.session import StartTestRequest, StartTestResponse, SubmitAnswersRequest
from SPTOVZ.utils.test_selector import select_test

# (опционально) если уже сделал движок расчётов — подключим
try:
    from SPTOVZ.utils.emspt_engine import compute_emspt, Profile  # noqa: F401
except Exception:
    compute_emspt = None
    Profile = None  # type: ignore

router = APIRouter(tags=["testing"])


# ---------------------------
# helpers
# ---------------------------

def _normalize(s: str) -> str:
    return (s or "").strip().lower()


def _get_institution_from_key(db: Session, key: Key) -> str:
    """
    Получаем тип учреждения через Key -> Group -> Class.
    У класса должно быть поле `education_type` со значениями:
    'school' | 'college' | 'university'.
    """
    group = db.get(Group, key.group_id) if key.group_id else None
    cls = group.class_ if group else (db.get(Class, key.class_id) if getattr(key, "class_id", None) else None)

    if not cls:
        raise HTTPException(status_code=400, detail="Ключ не привязан к классу/группе")

    if not hasattr(cls, "education_type") or not getattr(cls, "education_type"):
        raise HTTPException(
            status_code=500,
            detail="У класса отсутствует поле education_type. "
                   "Добавь его в модель Class (school|college|university) и перегенерируй БД."
        )

    inst = _normalize(cls.education_type)  # type: ignore[attr-defined]
    if inst not in {"school", "college", "university"}:
        raise HTTPException(status_code=400, detail=f"Некорректный education_type='{inst}' у класса")
    return inst


# ---------------------------
# /start-test
# ---------------------------

@router.post("/start-test", response_model=StartTestResponse)
def start_test(payload: StartTestRequest, db: Session = Depends(get_db)) -> StartTestResponse:
    # 1) Проверяем ключ
    key: Key | None = db.query(Key).filter(Key.code == payload.code).first()
    if not key:
        raise HTTPException(status_code=404, detail="Неверный код доступа")
    if getattr(key, "used", False):
        raise HTTPException(status_code=400, detail="Этот код уже использован")

    # 2) Подготавливаем выбор теста
    institution = _get_institution_from_key(db, key)          # school|college|university
    impairment = _normalize(payload.diagnosis)                 # hearing|vision|motor

    # 3) Выбираем тест (пол НЕ участвует)
    try:
        passport, content = select_test(db, institution=institution, impairment=impairment)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 4) Создаём сессию
    session = TestSession(
        id=str(uuid4()),
        key_id=key.id,
        age=payload.age,
        gender=_normalize(payload.gender),     # сохраняем для расчётов, но НЕ для выбора теста
        diagnosis=impairment,
        form_type=passport.form,               # "A" | "B" | "C"
        test_name=passport.title,
        started_at=datetime.utcnow(),
        answers=None,
        result=None,
    )
    if hasattr(key, "used"):
        key.used = True  # помечаем ключ использованным

    db.add(session)
    db.commit()
    db.refresh(session)

    # 5) Отдаём вопросы (это список dict из TestContent.questions)
    return StartTestResponse(
        session_id=session.id,
        test_name=passport.title,
        form_type=passport.form,
        questions=content.questions,  # List[dict]
    )


# ---------------------------
# /submit-answers
# ---------------------------

@router.post("/submit-answers")
def submit_answers(payload: SubmitAnswersRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    # 1) Сессия
    session: TestSession | None = db.get(TestSession, payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    if session.finished_at:
        raise HTTPException(status_code=400, detail="Сессия уже завершена")

    # 2) Определяем тест повторно (защитно на случай обновлений)
    key: Key | None = db.get(Key, session.key_id) if session.key_id else None
    if not key:
        raise HTTPException(status_code=400, detail="Сессия привязана к несуществующему ключу")

    institution = _get_institution_from_key(db, key)
    impairment = _normalize(session.diagnosis)

    try:
        passport, content = select_test(db, institution=institution, impairment=impairment)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 3) Приводим ответы к виду {question_id: value}
    q_order = [q.get("id") for q in (content.questions or [])]
    if all(isinstance(x, (int, float)) for x in payload.answers):
        if len(payload.answers) != len(q_order):
            raise HTTPException(status_code=400, detail="Количество ответов не совпадает с количеством вопросов")
        answers_map = {qid: int(value) for qid, value in zip(q_order, payload.answers)}
    else:
        tmp: Dict[Any, Any] = {}
        for item in payload.answers:  # ожидаем {"id": ..., "value": ...}
            if not isinstance(item, dict) or "id" not in item or "value" not in item:
                raise HTTPException(status_code=400, detail="Неверный формат ответа")
            tmp[item["id"]] = int(item["value"])
        answers_map = tmp

    # 4) Сохраняем сырые ответы
    session.answers = answers_map  # type: ignore[assignment]
    session.finished_at = datetime.utcnow()

    # 5) Считаем результат, если движок расчётов уже есть
    computed: Dict[str, Any] | None = None
    if compute_emspt and Profile:
        profile = Profile(
            form=passport.form,
            impairment=impairment,
            gender=_normalize(session.gender or "female"),  # "female"|"male"
        )
        computed = compute_emspt(answers_map, profile)

    session.result = computed
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "saved": True,
        "questions": len(q_order),
        "computed": computed is not None,
        "result": computed,
    }
