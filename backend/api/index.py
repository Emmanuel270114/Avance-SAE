from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from backend.core.templates import templates

router = APIRouter()

from backend.core.templates import templates

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
