from fastapi import FastAPI
from SPTOVZ.database import Base, engine

# Важно: импортируем модели, чтобы SQLAlchemy "увидел" таблицы
from SPTOVZ import models as _models  # noqa: F401
from SPTOVZ.routers import session as session_router
from SPTOVZ.routers import auth as auth_router
from SPTOVZ.routers import class_group as class_group_router
from SPTOVZ.routers import session as session_router

app = FastAPI(title="СПТ ОВЗ API")

# Создание таблиц (временно так, до миграций)
Base.metadata.create_all(bind=engine)

# Подключаем роутеры
app.include_router(auth_router.router)
app.include_router(class_group_router.router)
app.include_router(session_router.router)

@app.get("/")
def healthcheck():
    return {"status": "ok"}
