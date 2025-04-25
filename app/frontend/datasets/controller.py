from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from . import service

router = APIRouter(
    prefix="",
    tags=["frontend"],
)

templates = Jinja2Templates(directory="templates")

# ============================================================================
# Endpoints for the page: datasets.html
# ============================================================================

@router.get("/datasets", response_class=HTMLResponse)
async def get_datasets(request: Request):
    # Get the list of all datasets (with related data loaded)
    datasets = service.get_all_datasets()
    # Pass the list as "datasets" to the template.
    return templates.TemplateResponse(
        "datasets_page.html",
        {
            "request": request,
            "datasets": datasets,
        }
    )

@router.get("/datasets/{dataset_id}", response_class=HTMLResponse)
async def get_dataset_info(
    request: Request,
    dataset_id: int
    ):
    dataset, _, _ = service.get_dataset_info_by_id(dataset_id)
    return templates.TemplateResponse(
        "dataset_info.html",
        {"request": request, "dataset": dataset}
    )

@router.get("/datasets/{dataset_id}/files", response_class=HTMLResponse)
async def get_dataset_files(request: Request, dataset_id: int):
    dataset, total_files, analysed_files = service.get_dataset_info_by_id(dataset_id)
    return templates.TemplateResponse(
        "dataset_files_page.html", {"request": request, "dataset": dataset, "total_files": total_files, "analysed_files": analysed_files}
    )

@router.get("/datasets/{dataset_id}/files/all", response_class=HTMLResponse)
async def get_dataset_files_all(request: Request, dataset_id: int):
    all_files = service.get_all_files_from_dataset(dataset_id)
    return templates.TemplateResponse(
        "dataset_files_all_table.html", {"request": request, "all_files": all_files}
        )