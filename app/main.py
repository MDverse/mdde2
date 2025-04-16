import pathlib

from bokeh.embed import components
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .queries.common import (
    create_datasets_plot,
    create_files_plot,
    generate_title_wordcloud,
    get_all_datasets,
    get_dataset_info_by_id,
    get_dataset_origin_summary,
    get_file_type_stats,
    get_tsv_depending_on_type,
    get_all_files_from_dataset,
    get_param_files,
    get_top_files,
    get_traj_files,
)
from .routers import datatables


# ============================================================================
# FastAPI app
# ============================================================================
print(f"Running FastAPI app from: {pathlib.Path().absolute()}")

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(datatables.router)

# ============================================================================
# Endpoints for the page: index.html
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    # Generate the wordcloud image.
    generate_title_wordcloud()

    # Get the data from query
    datasets_stats_results, datasets_stats_total_count = get_dataset_origin_summary()
    

    # Create both Bokeh plots.
    files_plot = create_files_plot()
    datasets_plot = create_datasets_plot()

    # Get the script and div for each plot.
    files_plot_script, files_plot_div = components(files_plot)
    datasets_plot_script, datasets_plot_div = components(datasets_plot)

    # Pass it to the template
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "results": datasets_stats_results,
            "total_count": datasets_stats_total_count,
            "files_plot_script": files_plot_script,
            "files_plot_div": files_plot_div,
            "datasets_plot_script": datasets_plot_script,
            "datasets_plot_div": datasets_plot_div,
        }
    )


# ============================================================================
# Endpoints for the page: datasets.html
# ============================================================================

@app.get("/datasets", response_class=HTMLResponse)
async def search_page(request: Request):
    # Get the list of all datasets (with related data loaded)
    datasets = get_all_datasets()
    # Pass the list as "datasets" to the template.
    return templates.TemplateResponse(
        "datasets.html",
        {
            "request": request,
            "datasets": datasets,
        }
    )


@app.get("/dataset/{dataset_id}", response_class=HTMLResponse)
async def get_dataset_info(
    request: Request,
    dataset_id: int
    ):
    dataset, _, _ = get_dataset_info_by_id(dataset_id)
    return templates.TemplateResponse(
        "dataset_info.html",
        {"request": request, "dataset": dataset}
    )


# ============================================================================
# Endpoints for the page:   dataset_files_info.html
# ============================================================================

@app.get("/dataset/{dataset_id}/files", response_class=HTMLResponse)
async def dataset_files(request: Request, dataset_id: int):
    dataset, total_files, analysed_files = get_dataset_info_by_id(dataset_id)
    return templates.TemplateResponse(
        "dataset_file_info.html", {"request": request, "dataset": dataset, "total_files": total_files, "analysed_files": analysed_files}
    )


@app.get("/dataset/{dataset_id}/files/all_files", response_class=HTMLResponse)
async def dataset_all_files(request: Request, dataset_id: int):
    all_files = get_all_files_from_dataset(dataset_id)
    return templates.TemplateResponse(
        "file_table_template.html", {"request": request, "all_files": all_files}
        )


@app.get("/dataset/{dataset_id}/files/top_files", response_class=HTMLResponse)
async def dataset_top_files(request: Request, dataset_id: int):
    return templates.TemplateResponse(
        "topology_table_template.html", {"request": request, "dataset_id": dataset_id}
    )


@app.get("/dataset/{dataset_id}/files/param_files", response_class=HTMLResponse)
async def dataset_files(request: Request, dataset_id: int):
    param_files = get_param_files(dataset_id)
    return templates.TemplateResponse(
        "parameter_table_template.html", {"request": request, "param_files": param_files}
        )


@app.get("/dataset/{dataset_id}/files/traj_files", response_class=HTMLResponse)
async def dataset_files(request: Request, dataset_id: int):
    traj_files = get_traj_files(dataset_id)
    return templates.TemplateResponse(
        "trajectory_table_template.html", {"request": request, "traj_files": traj_files}
    )


# ============================================================================
# Endpoints for the page:   file_types.html
# ============================================================================

@app.get("/file_types", response_class=HTMLResponse)
async def file_types_table(request: Request):
    file_type_stats_summary = get_file_type_stats()
    return templates.TemplateResponse(
        "file_types.html",
        {
            "request": request,
            "file_type_stats_summary": file_type_stats_summary,
        }
    )

# Endpoint to render the file type download prompt snippet.
@app.get("/download_tsv/{file_type}", response_class=HTMLResponse)
async def download_tsv_files_for_file_type(request: Request, file_type: str):
    # Render a snippet with file type info and a download button.
    return templates.TemplateResponse(
        "file_type_download_prompt.html",
        {
            "request": request,
            "file_type": file_type,
        }
    )

# Endpoint to trigger the TSV file download.
@app.get("/download_tsv_file/{file_type}")
async def download_tsv_file(file_type: str):
    df = get_tsv_depending_on_type(file_type)
    tsv_data = df.to_csv(index=False, sep="\t")
    headers = {
        "Content-Disposition": f"attachment; filename=mdverse_{file_type}.tsv"
    }
    return Response(content=tsv_data, media_type="text/tsv", headers=headers)


# ============================================================================
# Endpoints for the page:   gro_file.html
# ============================================================================

@app.get("/gro_files", response_class=HTMLResponse)
async def gro_files_page(request: Request):
    return templates.TemplateResponse(
        "gro_files.html",
        {
            "request": request,
        }
    )

@app.get("/files/topologie/", response_class=JSONResponse)
async def all_gro_files_data(request: Request, dataset_id: int | None = None):
    """
    Get GRO files data for DataTables.

    See:
    - https://datatables.net/manual/server-side
    - https://blog.stackpuz.com/create-an-api-for-datatables-with-fastapi/

    Parameters
    ----------
    request : Request
        DataTables request parameters + optional dataset id.

    Returns
    -------
    dict
        JSON dictionnary for DataTables.
    """
    print("Hello from /files/topologie/")
    print("dataset_id", dataset_id)
    params = request.query_params.get
    sort_column_name = "dataset_origin"
    if params("order[0][column]"):
        sort_column_idx = params("order[0][column]")
        sort_column_name = params(f"columns[{sort_column_idx}][data]")
    sort_direction = "asc"
    if params("order[0][dir]") == "desc":
        sort_direction = "desc"
    number_of_top_files_total = len(get_top_files(dataset_id=dataset_id))
    number_of_top_files_filtered = len(get_top_files(
        dataset_id=dataset_id,
        search=params("search[value]"),
    ))
    top_files = get_top_files(
        dataset_id=dataset_id,
        sort_column_name=sort_column_name,
        sort_direction=sort_direction,
        start=params("start"),
        length=params("length"),
        search=params("search[value]"),
    )
    # Serialize SQLmodel results to JSON
    data = [ row._mapping for row in top_files ]
    return {
        "draw": params("draw"),
        "recordsTotal": number_of_top_files_total,
        "recordsFiltered": number_of_top_files_filtered,
        "data": data,
    }

# ============================================================================
# Endpoints for the page:   mdp_file.html
# ============================================================================

@app.get("/mdp_files", response_class=HTMLResponse)
def mdp_files_page(request: Request):
    return templates.TemplateResponse(
        "mdp_files.html",
        {
            "request": request,
        }
    )

@app.get("/all_mdp_files_data", response_class=JSONResponse)
def all_mdp_files_data():
    param_files = get_param_files()
    data = []
    for param_file_object,file_name, dataset_id_in_origin, dataset_url, dataset_origin, barostat_name, thermostat_name, integrator_name in param_files:
        data.append({
            "dataset_origin": dataset_origin if dataset_origin else "N/A",
            "dataset_url": dataset_url,
            "dataset_id_in_origin": dataset_id_in_origin,
            "file_name": file_name,
            "dt": param_file_object.dt,
            "nsteps": param_file_object.nsteps,
            "temperature": param_file_object.temperature,
            "thermostat_name": thermostat_name,
            "barostat_name": barostat_name,
            "integrator_name": integrator_name
        })
    return data
