"""Endpoints for the page: file_types"""

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from . import service

router = APIRouter(
    prefix="",
    tags=["frontend"],
)

templates = Jinja2Templates(directory="templates")


@router.get("/file_types", response_class=HTMLResponse)
async def file_types_table(request: Request):
    file_type_stats_summary = service.get_file_types_stats()
    return templates.TemplateResponse(
        "file_types_page.html",
        {
            "request": request,
            "file_type_stats_summary": file_type_stats_summary,
        }
    )

# Render the button to downlaod all files for a given file type.
# Endpoint triggered by HTMX.
@router.get("/file_types/{file_type}/download_info", response_class=HTMLResponse)
async def display_button_to_download_file_list(request: Request, file_type: str):
    return templates.TemplateResponse(
        "file_types_download_info.html",
        {
            "request": request,
            "file_type": file_type,
        }
    )

# Download the list of files for a given file type.
@router.get("/file_types/{file_type}/download_list/")
async def download_file_list(file_type: str):
    df = service.get_list_of_files_for_a_file_type(file_type)
    tsv_data = df.to_csv(index=False, sep="\t")
    headers = {
        "Content-Disposition": f"attachment; filename=mdverse_{file_type}.tsv"
    }
    return Response(content=tsv_data, media_type="text/tsv", headers=headers)