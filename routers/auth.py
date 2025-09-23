from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from uuid import uuid4

from database import get_db
from models.user import User
from schemas.user import UserCreate, UserResponse
from utils.auth import get_password_hash, verify_password

router = APIRouter(prefix="", tags=["auth"])

@router.post("/register", response_model=UserResponse)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=str(uuid4()),
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        education_type=payload.education_type,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    # Упростим: в access_token возвращаем id пользователя (JWT добавим позже)
    return {"access_token": user.id, "token_type": "bearer"}
