import pathlib


from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .queries.common import (
    get_param_files,
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
