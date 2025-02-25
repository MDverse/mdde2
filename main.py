from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from queries import get_dataset_origin_summary

app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.get("/")
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})