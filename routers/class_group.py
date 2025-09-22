from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4

from database import get_db
from models.class_group import Class, Group, Key
from models.user import User
from schemas.class_group import ClassCreate, GroupCreate, KeyResponse
from routers.auth import get_current_user

router = APIRouter(prefix="/class", tags=["class/group"])


# === Создание класса ===
@router.post("/create")
def create_class(data: ClassCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_class = Class(id=str(uuid4()), name=data.name, psychologist_id=user.id)
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return new_class


# === Создание группы в классе ===
@router.post("/group/create")
def create_group(data: GroupCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cls = db.query(Class).filter(Class.id == data.class_id, Class.psychologist_id == user.id).first()
    if not cls:
        raise HTTPException(status_code=403, detail="Invalid class or permission denied")

    new_group = Group(id=str(uuid4()), name=data.name, class_id=cls.id)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return new_group


# === Генерация ключа для группы ===
@router.post("/group/key/generate", response_model=KeyResponse)
def generate_key(group_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    cls = db.query(Class).filter(Class.id == group.class_id).first()
    if not cls or cls.psychologist_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    code = str(uuid4()).split("-")[0]  # короткий ключ
    key = Key(id=str(uuid4()), code=code, group_id=group.id, class_id=cls.id)

    db.add(key)
    db.commit()
    db.refresh(key)
    return key
