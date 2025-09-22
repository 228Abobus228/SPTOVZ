from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = "postgresql://postgres:your_password@localhost:5432/psychotest"

# Подключение к базе данных
engine = create_engine(DATABASE_URL)

# Создание сессии
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Базовый класс для моделей
Base = declarative_base()

# Функция-зависимость для FastAPI
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
