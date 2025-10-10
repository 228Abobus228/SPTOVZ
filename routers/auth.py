from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from uuid import uuid4

from SPTOVZ.database import get_db
from SPTOVZ.models.user import User
from SPTOVZ.models.institution import Institution
from SPTOVZ.schemas.user import UserCreate, UserResponse
from SPTOVZ.utils.auth import get_password_hash, verify_password

router = APIRouter(prefix="", tags=["auth"])

@router.post("/register", response_model=UserResponse)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    inst = Institution(
        id=str(uuid4()),
        name=payload.institution_name,
        education_type=payload.education_type,
    )
    user = User(
        id=str(uuid4()),
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        institution_id=inst.id,
    )
    db.add_all([inst, user])
    db.commit()
    db.refresh(user)
    return user

@router.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"access_token": user.id, "token_type": "bearer"}
