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
        total_size_in_GB,
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
                   .label("files"),

                # Sum size of all files in GB
                (func.sum(File.size_in_bytes) / 1e9).label("total_size_in_GB"),

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
            .outerjoin(File, File.dataset_id == Dataset.dataset_id)
            .outerjoin(FileType, File.file_type_id == FileType.file_type_id)
            .group_by(DatasetOrigin.name)
        )

        datasets_stats_results = session.exec(statement).all()

        datasets_stats_total_count = {
            "Number of datasets": "{:,}".format(sum(row.number_of_datasets for row in datasets_stats_results)),
            "First dataset": "nan",
            "Last dataset": "nan",
            "Files": "{:,}".format(sum(row.files for row in datasets_stats_results)),
            "Total size in GB": "{:,.0f}".format(sum(row.total_size_in_GB for row in datasets_stats_results)),
            "Zip files": "{:,}".format(sum(row.zip_files for row in datasets_stats_results)),
            "Files within zip files": "{:,}".format(sum(row.files_within_zip_files for row in datasets_stats_results)),
            "Total files": "{:,}".format(sum(row.total_files for row in datasets_stats_results)),
        }
        
        return datasets_stats_results, datasets_stats_total_count


# For file type stats, we want to retrieve:
# - the number of files per file type
# - the number of datasets per file type
# - the total size of files per file type
def get_file_type_stats():
    with Session(engine) as session:

        statement = (
            select(
            FileType.name.label("file_type"),
            func.count(func.distinct(File.file_id)).label("number_of_files"),
            func.count(func.distinct(Dataset.dataset_id)).label("number_of_datasets"),
            (func.sum(File.size_in_bytes) / 1e9).label("total_size_in_GB"),
            )
            .join(File, File.file_type_id == FileType.file_type_id)
            .outerjoin(Dataset, Dataset.dataset_id == File.dataset_id)
            .group_by(FileType.name)
        )
    
        file_type_stats_summary = session.exec(statement).all()

        return file_type_stats_summary