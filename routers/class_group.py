from __future__ import annotations
from uuid import uuid4
import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from SPTOVZ.database import get_db
from SPTOVZ.models.class_group import Class, Key
from SPTOVZ.models.user import User
from SPTOVZ.schemas.class_key import ClassCreate, ClassOut, KeyGenerateRequest, KeyOut
from SPTOVZ.utils.auth import get_current_user

router = APIRouter(prefix="/class", tags=["Class & Keys"])

_FORM_MAP = {"school": "A", "college": "B", "university": "C"}

def _gen_code(db: Session) -> str:
    # 10-символьный код A-Z0-9; проверяем уникальность
    while True:
        code = secrets.token_urlsafe(8).upper().replace("-", "")[:10]
        if not db.query(Key).filter(Key.code == code).first():
            return code

@router.post("/create", response_model=ClassOut)
def create_class(payload: ClassCreate,
                 db: Session = Depends(get_db),
                 me: User = Depends(get_current_user)):
    if not me.institution:
        raise HTTPException(status_code=400, detail="User has no institution")
    cls = Class(
        id=str(uuid4()),
        name=payload.name,
        teacher_id=me.id,
        institution_id=me.institution_id,
    )
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return ClassOut(id=cls.id, name=cls.name, education_type=cls.education_type)

@router.get("/my", response_model=List[ClassOut])
def my_classes(db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    classes = db.query(Class).filter(Class.teacher_id == me.id).all()
    return [ClassOut(id=c.id, name=c.name, education_type=c.education_type) for c in classes]

@router.post("/keys/generate", response_model=List[KeyOut])
def generate_keys(payload: KeyGenerateRequest,
                  db: Session = Depends(get_db),
                  me: User = Depends(get_current_user)):
    cls = db.get(Class, payload.class_id)
    if not cls or cls.teacher_id != me.id:
        raise HTTPException(status_code=404, detail="Class not found")
    edu = cls.education_type
    if edu not in _FORM_MAP:
        raise HTTPException(status_code=400, detail="Invalid education_type on class/institution")
    form = _FORM_MAP[edu]

    created: list[Key] = []
    for _ in range(max(1, int(payload.count))):
        key = Key(
            id=str(uuid4()),
            code=_gen_code(db),
            used=False,
            class_id=cls.id,
            education_type=edu,
            form_type=form,
        )
        db.add(key)
        created.append(key)
    db.commit()
    return [KeyOut(code=k.code, used=k.used, form_type=k.form_type, education_type=k.education_type) for k in created]
