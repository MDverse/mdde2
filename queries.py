from sqlalchemy import func, case
from sqlmodel import Session, select

from db_engine import engine
from db_models import Dataset, DatasetOrigin, File, FileType

# def get_dataset_origin_summary():
#     """
#     Returns a list of rows containing:
#         dataset_origin, number_of_datasets, first_dataset, last_dataset
#     """
#     with Session(engine) as session:
#         statement = (
#             select(
#                 DatasetOrigin.name.label("dataset_origin"),
#                 func.count(Dataset.dataset_id).label("number_of_datasets"),
#                 func.min(Dataset.date_created).label("first_dataset"),
#                 func.max(Dataset.date_created).label("last_dataset"),
#             )
#             .join(Dataset, Dataset.origin_id == DatasetOrigin.origin_id)
#             .group_by(DatasetOrigin.name)
#         )

#         results = session.exec(statement).all()

#         total_count = 0
#         for row in results:
#             total_count += row.number_of_datasets

#         return results, total_count


def get_dataset_origin_summary():
    """
    Returns rows grouped by dataset origin, with columns:
        dataset_origin,
        number_of_datasets,
        first_dataset,
        last_dataset,
        files (top-level),
        total_size_in_GB,
        zip_files (parent files that are zip),
        files_within_zip_files,
        total_files
    """
    with Session(engine) as session:
        statement = (
            select(
                DatasetOrigin.name.label("dataset_origin"),
                # Distinct dataset count
                func.count(func.distinct(Dataset.dataset_id)).label("number_of_datasets"),
                func.min(Dataset.date_created).label("first_dataset"),
                func.max(Dataset.date_created).label("last_dataset"),

                # Count top-level files (is_from_zip_file == False)
                func.count(File.file_id)
                   .filter(File.is_from_zip_file == False)
                   .label("files"),

                # Sum size of all files in GB
                (func.sum(File.size_in_bytes) / 1e9).label("total_size_in_GB"),

                # Count parent zip files (FileType.name == 'zip')
                func.count(File.file_id)
                   .filter(
                       (File.is_from_zip_file == False) &
                       (FileType.name == "zip")
                   )
                   .label("zip_files"),

                # Count files that are inside zip files
                func.count(File.file_id)
                   .filter(File.is_from_zip_file == True)
                   .label("files_within_zip_files"),

                # Total files (outside-non-zip_parent + parent zips + inside zips)
                func.count(File.file_id).label("total_files"),
            )
            .join(Dataset, Dataset.origin_id == DatasetOrigin.origin_id)
            .join(File, File.dataset_id == Dataset.dataset_id)
            .join(FileType, File.file_type_id == FileType.file_type_id, isouter=True)
            .group_by(DatasetOrigin.name)
        )

        datasets_stats_results = session.exec(statement).all()

        datasets_stats_total_count = {}
        datasets_stats_total_count["Number of datasets"] = sum(
            row.number_of_datasets for row in datasets_stats_results
        )
        datasets_stats_total_count["First dataset"] = None
        datasets_stats_total_count["Last dataset"] = None
        datasets_stats_total_count["Files"] = sum(
            row.files for row in datasets_stats_results
        )
        datasets_stats_total_count["Total size in GB"] = sum(
            row.total_size_in_GB for row in datasets_stats_results
        )
        datasets_stats_total_count["Zip files"] = sum(
            row.zip_files for row in datasets_stats_results
        )
        datasets_stats_total_count["Files within zip files"] = sum(
            row.files_within_zip_files for row in datasets_stats_results
        )
        datasets_stats_total_count["Total files"] = sum(
            row.total_files for row in datasets_stats_results
        )

        return datasets_stats_results, datasets_stats_total_count
    

# For file type stats, we want to retrieve:
# - the number of files per file type
# - the number of datasets per file type
# - the total size of files per file type
def file_type_stats():
    with Session(engine) as session:
        statement = (
            select(
                FileType.name.label("file_type"),
                func.count(File.file_id).label("number_of_files"),
                func.count(Dataset.dataset_id).label("number_of_datasets"),
                (func.sum(File.size_in_bytes) / 1e9).label("total_size_in_GB"),
            )
            .join(File, File.file_type_id == FileType.file_type_id)
            .join(Dataset, Dataset.dataset_id == File.dataset_id)
            .group_by(FileType.name)
        )
    
        file_type_stats_summary = session.exec(statement).all()
        return file_type_stats_summary