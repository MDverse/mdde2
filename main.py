from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from queries import get_dataset_origin_summary, get_file_type_stats

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index(request: Request):
    # Get the data your query
    datasets_stats_results, datasets_stats_total_count = get_dataset_origin_summary()
    file_type_stats_summary = get_file_type_stats()

    # Pass it to the template
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "results": datasets_stats_results,
            "total_count": datasets_stats_total_count,
            "file_type_stats_summary": file_type_stats_summary,
        }
    )

