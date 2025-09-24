from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4

from SPTOVZ.database import get_db
from SPTOVZ.models.class_group import Class, Group, Key
from SPTOVZ.schemas.class_group import (
    ClassCreate, ClassOut,
    GroupCreate, GroupOut,
    GenerateKeysRequest, KeyOut
)


router = APIRouter(prefix="", tags=["structure"])

# Классы
@router.post("/classes", response_model=ClassOut)
def create_class(payload: ClassCreate, db: Session = Depends(get_db)):
    cls = Class(id=str(uuid4()), name=payload.name, psychologist_id=payload.psychologist_id)
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return cls

@router.get("/classes", response_model=list[ClassOut])
def list_classes(psychologist_id: str, db: Session = Depends(get_db)):
    return db.query(Class).filter(Class.psychologist_id == psychologist_id).all()

# Группы
@router.post("/groups", response_model=GroupOut)
def create_group(payload: GroupCreate, db: Session = Depends(get_db)):
    cls = db.query(Class).get(payload.class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    grp = Group(id=str(uuid4()), name=payload.name, class_id=payload.class_id)
    db.add(grp)
    db.commit()
    db.refresh(grp)
    return grp

@router.get("/classes/{class_id}/groups", response_model=list[GroupOut])
def list_groups(class_id: str, db: Session = Depends(get_db)):
    return db.query(Group).filter(Group.class_id == class_id).all()

# Ключи
def _new_code(db: Session) -> str:
    # простой генератор кода: 8 символов, заглавные; при коллизии — генерим заново
    import random, string
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not db.query(Key).filter(Key.code == code).first():
            return code

@router.post("/groups/{group_id}/keys", response_model=list[KeyOut])
def generate_keys(group_id: str, payload: GenerateKeysRequest, db: Session = Depends(get_db)):
    grp = db.query(Group).get(group_id)
    if not grp:
        raise HTTPException(status_code=404, detail="Group not found")
    n = max(1, payload.count)
    keys = []
    for _ in range(n):
        k = Key(id=str(uuid4()), code=_new_code(db), used=False, group_id=group_id)
        db.add(k)
        keys.append(k)
    db.commit()
    return keys

@router.get("/groups/{group_id}/keys", response_model=list[KeyOut])
def list_keys(group_id: str, db: Session = Depends(get_db)):
    return db.query(Key).filter(Key.group_id == group_id).all()
