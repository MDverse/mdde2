from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from . import service

router = APIRouter(
    prefix="/datatables",
    tags=["datatables"],
)
