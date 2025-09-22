from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = "postgresql://spt:jnDUYk3f43543545hldjfhjkpzYYjdlhGPKnvhe4334@spt.one:11697/spt_ovz"

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
