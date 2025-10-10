from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from SPTOVZ.database import Base, engine
from SPTOVZ import models
from SPTOVZ.routers import auth as auth_router, class_group as class_router, session as session_router

app = FastAPI(title="СПТ ОВЗ")
Base.metadata.create_all(bind=engine)

app.include_router(auth_router.router)
app.include_router(class_router.router)
app.include_router(session_router.router)

templates = Jinja2Templates(directory="SPTOVZ/templates")

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/testing", response_class=HTMLResponse)
def testing(request: Request):
    return templates.TemplateResponse("testing.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("SPTOVZ.main:app", host="127.0.0.1", port=8000, reload=True)
