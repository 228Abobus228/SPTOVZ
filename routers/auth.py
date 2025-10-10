from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from SPTOVZ.database import get_db
from SPTOVZ.models.user import User
from SPTOVZ.models.institution import Institution
from SPTOVZ.utils.auth import verify_password

from SPTOVZ.database import get_db
from SPTOVZ.models.user import User
from SPTOVZ.models.institution import Institution
from SPTOVZ.schemas.user import UserCreate, UserResponse
from SPTOVZ.utils.auth import get_password_hash, verify_password
from SPTOVZ.utils.auth import get_current_user
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends
from SPTOVZ.database import get_db
from SPTOVZ.models.user import User
from SPTOVZ.models.institution import Institution

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
router = APIRouter(tags=["auth"])

@router.get("/me")
def get_profile(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Возвращает профиль пользователя по токену (user.id)
    """
    user = db.query(User).filter(User.id == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Not Found")

    institution = db.query(Institution).filter(Institution.id == user.institution_id).first()

    return {
        "email": user.email,
        "institution_name": institution.name if institution else None,
        "education_type": institution.education_type if institution else None
    }


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
    """
    Упрощённая авторизация: токен = id пользователя.
    """
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    return {"access_token": user.id, "token_type": "bearer"}