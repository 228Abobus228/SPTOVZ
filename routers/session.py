from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from SPTOVZ.database import get_db
from SPTOVZ.models.class_group import Key
from SPTOVZ.models.session import TestSession
from SPTOVZ.schemas.session import StartTestRequest, StartTestResponse
from SPTOVZ.utils.test_selector import select_test

router = APIRouter(prefix="", tags=["testing"])


@router.post("/start-test", response_model=StartTestResponse)
def start_test(payload: StartTestRequest, db: Session = Depends(get_db)):
    key = db.query(Key).filter(Key.code == payload.code).first()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    if key.used:
        raise HTTPException(status_code=400, detail="Key already used")

    # Вытаскиваем тип учреждения через цепочку связей
    education_type = None
    if key.group and key.group.class_ and key.group.class_.psychologist:
        education_type = key.group.class_.psychologist.education_type

    try:
        form_type, test_name = select_test(education_type, payload.diagnosis)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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

    return StartTestResponse(
        session_id=session.id,
        test_name=test_name,
        form_type=form_type,
        questions=[]
    )