from __future__ import annotations
from uuid import uuid4
import secrets
from typing import List
from fastapi import Query
from SPTOVZ.models.class_group import Key
from SPTOVZ.models.institution import Institution
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from SPTOVZ.database import get_db
from SPTOVZ.models.class_group import Class, Key
from SPTOVZ.models.user import User
from SPTOVZ.schemas.class_key import ClassCreate, ClassOut, KeyGenerateRequest, KeyOut
from SPTOVZ.utils.auth import get_current_user

router = APIRouter(prefix="/class", tags=["Classes"])

_FORM_MAP = {"school": "A", "college": "B", "university": "C"}

def _gen_code(db: Session) -> str:
    # 10-символьный код A-Z0-9; проверяем уникальность
    while True:
        code = secrets.token_urlsafe(8).upper().replace("-", "")[:10]
        if not db.query(Key).filter(Key.code == code).first():
            return code

@router.post("/create", response_model=ClassOut)
def create_class(payload: ClassCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Создаёт класс, автоматически привязанный к пользователю и учреждению.
    """
    if not user.institution_id:
        raise HTTPException(status_code=400, detail="У пользователя нет учреждения")

    new_class = Class(
        id=str(uuid4()),
        name=payload.name,
        teacher_id=user.id,
        institution_id=user.institution_id,
    )
    db.add(new_class)
    db.commit()
    db.refresh(new_class)

    return new_class

@router.get("/", response_model=list[ClassOut])
def list_classes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Возвращает все классы, созданные данным пользователем.
    """
    classes = db.query(Class).filter(Class.teacher_id == user.id).all()
    return classes


@router.get("/my", response_model=List[ClassOut])
def my_classes(db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    classes = db.query(Class).filter(Class.teacher_id == me.id).all()
    return [ClassOut(id=c.id, name=c.name, education_type=c.education_type) for c in classes]

@router.post("/generate-keys")
def generate_keys(
    class_id: str,
    count: int = Query(1, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Создаёт коды тестирования для указанного класса.
    Автоматически подтягивает форму A/B/C исходя из учреждения пользователя.
    """
    # Проверяем, что класс принадлежит этому пользователю
    target_class = db.query(Class).filter(
        Class.id == class_id,
        Class.teacher_id == user.id
    ).first()

    if not target_class:
        raise HTTPException(status_code=404, detail="Класс не найден")

    # Получаем учреждение пользователя
    institution = db.query(Institution).filter(Institution.id == user.institution_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Учреждение не найдено")

    # Определяем форму по типу учреждения
    type_map = {
        "school": "A",
        "college": "B",
        "university": "C",
        "a": "A",
        "b": "B",
        "c": "C"
    }
    form_type = type_map.get(institution.education_type.lower())
    if not form_type:
        raise HTTPException(status_code=400, detail="Неизвестный тип учреждения")

    # Генерируем коды
    new_keys = []
    for _ in range(count):
        code = secrets.token_hex(3).upper()  # 6-значный код, например "A3F91B"
        key = Key(
            id=str(uuid4()),
            code=code,
            used=False,
            class_id=target_class.id,
            education_type=institution.education_type,
            form_type=form_type
        )
        db.add(key)
        new_keys.append(code)

    db.commit()

    return {"generated": new_keys, "form": form_type, "education_type": institution.education_type}

@router.post("/keys/generate")
def generate_keys_alias(
    class_id: str,
    count: int = 1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Обёртка для старого пути /class/keys/generate.
    Делает то же самое, что /classes/generate-keys.
    """
    return generate_keys(class_id=class_id, count=count, db=db, user=user)