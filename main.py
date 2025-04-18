from bokeh.embed import components
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from queries import (
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

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# ============================================================================
# Endpoints for the page:   index.html
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
# Endpoints for the page:   search.html
# ============================================================================

@app.get("/search", response_class=HTMLResponse)
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
    top_files = get_top_files(dataset_id)
    return templates.TemplateResponse(
        "topology_table_template.html", {"request": request, "top_files": top_files}
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

@app.get("/all_gro_files_data", response_class=JSONResponse)
async def all_gro_files_data():
    top_files = get_top_files()
    data = []
    for top_file_object, file_name, dataset_id_in_origin, dataset_url, dataset_origin in top_files:
        data.append({
            "dataset_origin": dataset_origin if dataset_origin else "N/A",
            "dataset_url": dataset_url,
            "dataset_id_in_origin": dataset_id_in_origin,
            "file_name": file_name,
            "atom_number": top_file_object.atom_number,
            "has_protein": top_file_object.has_protein,
            "has_nucleic": top_file_object.has_nucleic,
            "has_lipid": top_file_object.has_lipid,
            "has_glucid": top_file_object.has_glucid,
            "has_water_ion": top_file_object.has_water_ion
        })
    return data


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
