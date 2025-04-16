import pandas as pd
from sqlalchemy import desc
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select, or_

from ..db_schema import (
    Dataset,
    DatasetKeywordLink,
    DatasetAuthorLink,
    DatasetOrigin,
    File,
    FileType,
    Keyword,
    Author,
    ParameterFile,
    TopologyFile,
    TrajectoryFile,
    Barostat,
    Integrator,
    Thermostat,
    engine,
)


def get_all_datasets(
        sort_column_name: str | None = None,
        sort_direction: str | None = "asc",
        start: int | None = None,
        length: int | None = None,
        search: str | None = None,
    ) -> list[Dataset]:
    """
    Returns a list of all dataset, with their related fields.
    """
    statement = (
        select(
            DatasetOrigin.name.label("dataset_origin"),
            Dataset.id_in_origin.label("dataset_id_in_origin"),
            Dataset.dataset_id,
            Dataset.title,
            Dataset.description,
            Dataset.date_created,
            Dataset.date_last_modified,
            Dataset.file_number,
            Dataset.download_number,
            Dataset.view_number,
            Dataset.url,
        )
        .join(DatasetOrigin, Dataset.origin_id == DatasetOrigin.origin_id)
    )

    if sort_column_name is not None:
        if sort_direction == "asc":
            statement = statement.order_by(sort_column_name)
        elif sort_direction == "desc":
            statement = statement.order_by(desc(sort_column_name))

    if start is not None:
        statement = statement.offset(start)

    if length is not None:
        statement = statement.limit(length)

    if search is not None:
        statement = statement.where(or_(
            DatasetOrigin.name.ilike(f"%{search}%"),
            Dataset.id_in_origin.ilike(f"%{search}%"),
            Dataset.title.ilike(f"%{search}%"),
            Dataset.description.ilike(f"%{search}%"),
        ))
    with Session(engine) as session:
        results = session.exec(statement).all()
        # df = pd.read_sql_query(statement, session.bind)
        # print(df.columns)
        return results
