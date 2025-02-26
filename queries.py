from sqlalchemy import func
from sqlmodel import Session, select

from db_engine import engine
from db_models import Dataset, DatasetOrigin

def get_dataset_origin_summary():
    """
    Returns a list of rows containing:
        dataset_origin, number_of_datasets, first_dataset, last_dataset
    """
    with Session(engine) as session:
        statement = (
            select(
                DatasetOrigin.name.label("dataset_origin"),
                func.count(Dataset.dataset_id).label("number_of_datasets"),
                func.min(Dataset.date_created).label("first_dataset"),
                func.max(Dataset.date_created).label("last_dataset"),
            )
            .join(Dataset, Dataset.origin_id == DatasetOrigin.origin_id)
            .group_by(DatasetOrigin.name)
        )

        results = session.exec(statement).all()

        total_count = 0
        for row in results:
            total_count += row.number_of_datasets

        return results, total_count
