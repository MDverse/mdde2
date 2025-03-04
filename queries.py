from sqlalchemy import func

from sqlmodel import Session, select

from db_engine import engine
from db_models import Dataset, DatasetOrigin, File, FileType

def get_dataset_origin_summary():
    """
    Returns rows grouped by dataset origin, with columns:
        dataset_origin,
        number_of_datasets,
        first_dataset,
        last_dataset,
        files (top-level),
        total_size_in_GB_non_zip_and_zip_files,
        zip_files (parent files that are zip),
        files_within_zip_files,
        total_files
    """
    with Session(engine) as session:
        statement = (
            select(
                # Dataset stats
                DatasetOrigin.name.label("dataset_origin"),
                func.count(func.distinct(Dataset.dataset_id)).label("number_of_datasets"),
                func.min(Dataset.date_created).label("first_dataset"),
                func.max(Dataset.date_created).label("last_dataset"),

                # Count files that are not zip files, also is_from_zip_file == False
                func.count(func.distinct(File.file_id))
                   .filter(
                       (File.is_from_zip_file == False),
                       (FileType.name != "zip")
                       )
                   .label("non_zip_files"),

                # Sum size of files that has is_from_zip_file == False
                (func.sum(File.size_in_bytes).filter(File.is_from_zip_file == False)/ 1e9
                ).label("total_size_in_GB_non_zip_and_zip_files"),

                # Count parent zip files (FileType.name == 'zip')
                func.count(func.distinct(File.file_id))
                   .filter(
                       (File.is_from_zip_file == False) &
                       (FileType.name == "zip")
                   )
                   .label("zip_files"),

                # Count files that are inside zip files
                func.count(func.distinct(File.file_id))
                   .filter(File.is_from_zip_file == True)
                   .label("files_within_zip_files"),

                # Total files (outside-non-zip_parent + parent zips + inside zips)
                func.count(func.distinct(File.file_id)).label("total_files"),
            )
            .join(Dataset, Dataset.origin_id == DatasetOrigin.origin_id)
            # We have to do an outerjoin here because there are some datasets with no files
            # For example some osf datasets have no files
            .outerjoin(File, File.dataset_id == Dataset.dataset_id)
            .outerjoin(FileType, File.file_type_id == FileType.file_type_id)
            .group_by(DatasetOrigin.name)
        )

        datasets_stats_results = session.exec(statement).all()

        datasets_stats_total_count = {
            "Number of datasets": "{:,}".format(sum(row.number_of_datasets for row in datasets_stats_results)),
            "First dataset": "nan",
            "Last dataset": "nan",
            "Non-zip files": "{:,}".format(sum(row.non_zip_files for row in datasets_stats_results)),
            "Zip files": "{:,}".format(sum(row.zip_files for row in datasets_stats_results)),
            "Files in zip files": "{:,}".format(sum(row.files_within_zip_files for row in datasets_stats_results)),
            "Total files": "{:,}".format(sum(row.total_files for row in datasets_stats_results)),
            "Total size in GB for non-zip and zip files ": "{:,.0f}".format(sum(row.total_size_in_GB_non_zip_and_zip_files for row in datasets_stats_results)),
        }
        
        return datasets_stats_results, datasets_stats_total_count


def get_file_type_stats():
    """
    Retrieves statistics for each file type, including:
    - the number of files per file type,
    - the number of datasets per file type,
    - the total size of files per file type in gigabytes.

    Returns:
    file_type_stats_summary (list): A list of results where each result is a row containing:
        - file_type (str): The name of the file type.
        - number_of_files (int): The count of files for this file type.
        - number_of_datasets (int): The count of datasets containing files of this file type.
        - total_size_in_GB (float): The total size of files for this file type in gigabytes.
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
            # .order_by(func.count(func.distinct(File.file_id)).desc())
            # order_by could be used to sort the results by the number of files per file type
            # but it is not necessary for this example because the template will sort the results
            # in the frontend using the DataTables options
        )
    
        file_type_stats_summary = session.exec(statement).all()

        return file_type_stats_summary