import pathlib


from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .queries.common import (
    get_param_files,
    get_top_files,
    get_traj_files,
)


from .frontend.controller import router as frontend_router
from .frontend.datasets.controller import router as frontend_dataset_router
from .frontend.file_types.controller import router as frontend_file_types_router

# ============================================================================
# FastAPI app
# ============================================================================
print(f"Running FastAPI app from: {pathlib.Path().absolute()}")

app = FastAPI()


app.mount("/static", StaticFiles(directory="static"), name="static")

# Frontend endpoints
app.include_router(frontend_router)
app.include_router(frontend_dataset_router)
app.include_router(frontend_file_types_router)

templates = Jinja2Templates(directory="templates")





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
