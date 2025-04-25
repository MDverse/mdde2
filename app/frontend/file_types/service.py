"""SQL queries for file types"""

import pandas as pd
from sqlalchemy import extract, func, case, desc
from sqlalchemy.orm import selectinload, aliased
from sqlmodel import Session, select, or_, col
from typing import Optional

from ...db_schema import (
    Dataset,
    DatasetKeywordLink,
    DatasetOrigin,
    File,
    FileType,
    Keyword,
    ParameterFile,
    TopologyFile,
    TrajectoryFile,
    Barostat,
    Integrator,
    Thermostat,
    engine,
)


def get_file_types_stats():
    """
    Retrieves statistics for each file type, including:
    - the number of files per file type,
    - the number of datasets per file type,
    - the total size of files per file type in gigabytes.

    Returns:
    file_type_stats_summary (list): A list of results where
    each result is a row containing:
        - file_type (str): The name of the file type.
        - number_of_files (int): The count of files for this file type.
        - number_of_datasets (int): The count of datasets containing
                                    files of this file type.
        - total_size_in_GB (float): The total size of files for this
                                    file type in gigabytes.
    """
    with Session(engine) as session:
        statement = (
            select(
            FileType.name.label("file_type"),
            func.count(File.file_id).label("number_of_files"),
            func.count(func.distinct(Dataset.dataset_id)).label("number_of_datasets"),
            (func.sum(File.size_in_bytes) / 1e9).label("total_size_in_GB"),
            )
            .join(File, File.file_type_id == FileType.file_type_id)
            .outerjoin(Dataset, Dataset.dataset_id == File.dataset_id)
            .group_by(FileType.name)
            .order_by(func.count(func.distinct(File.file_id)).desc())
        )
        file_type_stats_summary = session.exec(statement).all()
        return file_type_stats_summary


def get_list_of_files_for_a_file_type(file_type: str) -> pd.DataFrame:
    """
    Returns a DataFrame with all files of a given file type.
    """
    # Create an alias for the parent file
    ParentFile = aliased(File)
    
    # Define a CASE expression: if file is from a zip, then use parent's URL, else use file.url
    file_url_expr = case(
        (File.is_from_zip_file == True, ParentFile.url),
        else_=File.url
    ).label("file_url")

    with Session(engine) as session:
        statement = (
            select(
                Dataset.id_in_origin.label("dataset_id"),
                DatasetOrigin.name.label("dataset_origin"),
                File.name.label("file_name"),
                File.size_in_bytes.label("file_size_in_bytes"),
                File.is_from_zip_file.label("is_file_from_zip_file"),
                file_url_expr,
                Dataset.url.label("dataset_url"),
            )
            .join(FileType, File.file_type_id == FileType.file_type_id)
            .join(Dataset, File.dataset_id == Dataset.dataset_id)
            .join(DatasetOrigin, Dataset.origin_id == DatasetOrigin.origin_id)
            # Left join the parent file so that files from a zip can retrieve the parent URL.
            .join(ParentFile, File.parent_zip_file_id == ParentFile.file_id, isouter=True)
            .where(FileType.name == file_type)
        )
        results = session.exec(statement).all()
        # Convert results to a list of dictionaries then to a DataFrame
        data = [dict(row._mapping) for row in results]
        df = pd.DataFrame(data)
        return df
