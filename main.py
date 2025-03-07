from typing import Annotated, Union

from fastapi import FastAPI, Request, Header
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from queries import (
    get_dataset_origin_summary,
    get_file_type_stats,
    get_all_datasets,
    generate_keyword_wordcloud,
    get_dataset_by_id,
)

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index(request: Request):
    # Generate the wordcloud image.
    generate_keyword_wordcloud()


    # Get the data from query
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


@app.get("/search")
async def search_page(request: Request):
    # Get the list of all datasets (with related data loaded)
    datasets = get_all_datasets()
    # Pass the list as "datasets" to the template.
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "datasets": datasets,
        }
    )


@app.get("/dataset/{dataset_id}")
async def get_dataset_info(
    request: Request,
    dataset_id: int
    ):
    dataset = get_dataset_by_id(dataset_id)
    return templates.TemplateResponse(
        "dataset_info.html",
        {"request": request, "dataset": dataset}
    )