from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Boolean, ForeignKey, Integer, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from passlib.context import CryptContext
from uuid import uuid4
from datetime import datetime

DATABASE_URL = "postgresql://postgres:your_password@localhost:5432/psychotest"
#fsdfjhkjjeфыва

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ====== SQLAlchemy модели ======
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    classes = relationship("Class", back_populates="psychologist")

class Class(Base):
    __tablename__ = "classes"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    psychologist_id = Column(String, ForeignKey("users.id"))
    psychologist = relationship("User", back_populates="classes")
    groups = relationship("Group", back_populates="class_")

class Group(Base):
    __tablename__ = "groups"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_id = Column(String, ForeignKey("classes.id"))
    class_ = relationship("Class", back_populates="groups")
    keys = relationship("Key", back_populates="group")

class Key(Base):
    __tablename__ = "keys"
    id = Column(String, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)
    used = Column(Boolean, default=False)
    group_id = Column(String, ForeignKey("groups.id"))
    class_id = Column(String, ForeignKey("classes.id"))
    group = relationship("Group", back_populates="keys")

class TestSession(Base):
    __tablename__ = "test_sessions"
    id = Column(String, primary_key=True, index=True)
    key_id = Column(String, ForeignKey("keys.id"))
    age = Column(Integer)
    gender = Column(String)
    diagnosis = Column(String)
    form_type = Column(String)
    test_name = Column(String)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    answers = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)

Base.metadata.create_all(bind=engine)

# ====== Pydantic схемы ======
class UserCreate(BaseModel):
    email: str
    password: str

class ClassCreate(BaseModel):
    name: str

class GroupCreate(BaseModel):
    name: str
    class_id: str

class KeyResponse(BaseModel):
    id: str
    code: str

class StartTestRequest(BaseModel):
    code: str
    age: int
    gender: str
    diagnosis: str


class StartTestResponse(BaseModel):
    session_id: str
    test_name: str
    form_type: str

# ====== Зависимости ======
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ====== Аутентификация ======
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user

@app.post("/register")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(id=str(uuid4()), email=user_data.email, password_hash=get_password_hash(user_data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User registered successfully"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"access_token": user.email, "token_type": "bearer"}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    return user

# ====== Классы и группы ======
@app.post("/class/create")
def create_class(data: ClassCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_class = Class(id=str(uuid4()), name=data.name, psychologist_id=user.id)
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return new_class

@app.post("/group/create")
def create_group(data: GroupCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cls = db.query(Class).filter(Class.id == data.class_id, Class.psychologist_id == user.id).first()
    if not cls:
        raise HTTPException(status_code=403, detail="Invalid class or permission denied")
    new_group = Group(id=str(uuid4()), name=data.name, class_id=cls.id)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return new_group

# ====== Генерация ключей ======
@app.post("/key/generate", response_model=KeyResponse)
def generate_key(group_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    cls = db.query(Class).filter(Class.id == group.class_id).first()
    if not cls or cls.psychologist_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    code = str(uuid4()).split("-")[0]
    key = Key(id=str(uuid4()), code=code, group_id=group.id, class_id=cls.id)
    db.add(key)
    db.commit()
    db.refresh(key)
    return key

# ====== Начало теста ребёнком ======
@app.post("/start-test", response_model=StartTestResponse)
def start_test(data: StartTestRequest, db: Session = Depends(get_db)):
    key = db.query(Key).filter(Key.code == data.code).first()
    if not key:
        raise HTTPException(status_code=404, detail="Invalid key")
    if key.used:
        raise HTTPException(status_code=400, detail="Key already used")

    # Пока логика выбора формы и теста простая (заглушка)
    form_type = "A"
    test_name = "Тест уверенности"

    session = TestSession(
        id=str(uuid4()),
        key_id=key.id,
        age=data.age,
        gender=data.gender,
        diagnosis=data.diagnosis,
        form_type=form_type,
        test_name=test_name,
        started_at=datetime.utcnow()
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return StartTestResponse(
        session_id=session.id,
        test_name=test_name,
        form_type=form_type
    )
