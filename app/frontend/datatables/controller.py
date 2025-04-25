from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from . import service

router = APIRouter(
    prefix="/datatables",
    tags=["datatables"],
)

@router.get("/datasets", response_class=JSONResponse)
async def get_all_datasets(request: Request):
    """
    Get all datasets for DataTables.

    See:
    - https://datatables.net/manual/server-side
    - https://blog.stackpuz.com/create-an-api-for-datatables-with-fastapi/

    Parameters
    ----------
    request : Request
        DataTables request parameters

    Returns
    -------
    dict
        JSON dictionnary for DataTables.
    """
    params = request.query_params.get
    sort_column_name = "dataset_origin"
    if params("order[0][column]"):
        sort_column_idx = params("order[0][column]")
        sort_column_name = params(f"columns[{sort_column_idx}][data]")
    sort_direction = "asc"
    if params("order[0][dir]") == "desc":
        sort_direction = "desc"
    number_of_datasets_total = len(service.get_all_datasets())
    number_of_datasets_filtered = len(service.get_all_datasets(
        search=params("search[value]"),
    ))
    datasets = service.get_all_datasets(
        sort_column_name=sort_column_name,
        sort_direction=sort_direction,
        start=params("start"),
        length=params("length"),
        search=params("search[value]"),
    )
    # Serialize SQLmodel results to JSON
    data = [row._mapping for row in datasets]
    return {
        "draw": params("draw"),
        "recordsTotal": number_of_datasets_total,
        "recordsFiltered": number_of_datasets_filtered,
        "data": data,
    }
