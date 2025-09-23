from fastapi import FastAPI
from database import Base, engine
from routers import auth as auth_router
from routers import class_group as class_group_router
from routers import session as session_router

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
