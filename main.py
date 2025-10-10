from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from SPTOVZ.database import Base, engine
from SPTOVZ import models
from SPTOVZ.routers import session as session_router, class_group as class_router
from SPTOVZ.routers import auth as auth_router
from SPTOVZ.routers import (
    session as session_router,
    auth as auth_router,
    class_group as class_group_router
)

app = FastAPI(title="СПТ ОВЗ API")

# Создание таблиц (временно так, до миграций)
Base.metadata.create_all(bind=engine)

# Подключаем роутеры
app.include_router(auth_router.router)
app.include_router(class_group_router.router)
app.include_router(session_router.router)

templates = Jinja2Templates(directory="SPTOVZ/templates")

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/testing", response_class=HTMLResponse)
def testing(request: Request):
    return templates.TemplateResponse("testing.html", {"request": request})