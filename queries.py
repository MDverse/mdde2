from pathlib import Path

import time
from datetime import timedelta

import pandas as pd
import matplotlib.pyplot as plt
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from sqlalchemy import extract, func, case, desc
from sqlalchemy.orm import selectinload, aliased
from sqlmodel import Session, select, or_, col
from wordcloud import STOPWORDS, WordCloud
from typing import Optional

from db_schema import (
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

# ============================================================================
# Queries for index.html
# ============================================================================


def get_dataset_origin_summary() -> tuple[list[any], dict[str, str]]:
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
                   .filter(File.is_from_zip_file)
                   .label("files_within_zip_files"),

                # Total files (outside-non-zip_parent + parent zips + inside zips)
                func.count(func.distinct(File.file_id)).label("total_files"),
            )
            .join(Dataset, Dataset.origin_id == DatasetOrigin.origin_id)
            # We have to do an outerjoin here because
            # there are some datasets with no files
            # For example some osf datasets have no files
            .outerjoin(File, File.dataset_id == Dataset.dataset_id)
            .outerjoin(FileType, File.file_type_id == FileType.file_type_id)
            .group_by(DatasetOrigin.name)
        )

        datasets_stats_results = session.exec(statement).all()

        datasets_stats_total_count = {
            "Number of datasets": "{:,}".format(sum(
            row.number_of_datasets for row in datasets_stats_results
            )),
            "First dataset": min(
            row.first_dataset for row in datasets_stats_results
            ) if any(row.first_dataset for row in datasets_stats_results) else None,
            "Last dataset": max(
            row.last_dataset for row in datasets_stats_results
            ) if any(row.last_dataset for row in datasets_stats_results) else None,
            "Non-zip files": "{:,}".format(sum(
            row.non_zip_files for row in datasets_stats_results
            )),
            "Zip files": "{:,}".format(sum(
            row.zip_files for row in datasets_stats_results
            )),
            "Files in zip files": "{:,}".format(sum(
            row.files_within_zip_files for row in datasets_stats_results
            )),
            "Total files": "{:,}".format(sum(
            row.total_files for row in datasets_stats_results
            )),
            "Total size in GB for non-zip and zip files ": "{:,.0f}".format(sum(
            row.total_size_in_GB_non_zip_and_zip_files for row in datasets_stats_results
            )),
        }

        return datasets_stats_results, datasets_stats_total_count


def get_titles():
    with Session(engine) as session:
        statement = select(Dataset.title)
        titles = session.exec(statement).all()
    return titles


def generate_title_wordcloud():
    wordcloud_path = Path("static/wordcloud.png")

    # Check if the file already exists
    if wordcloud_path.exists():
        print("Wordcloud already exists, skipping generation.")
        return

    # Retrieve dataset titles using the query function
    titles = get_titles()  # e.g. ['Dataset Title 1', 'Dataset Title 2', ...]

    # Join all titles into a single string (space separated)
    text = " ".join(titles)

    # Define custom stopwords to remove unwanted words (adjust as needed)
    custom_stopwords = set(STOPWORDS)
    custom_stopwords.update([
        "none",
        "and",
        "of",
        "with",
        ",",
        "which",
        "incl",
        "from",
        "the",
        "a",
        "an",
        "for",
        "on",
        "in",
        "to",
        "by",
        "as",
        ])

    # Create the WordCloud object with the desired resolution settings
    wordcloud = WordCloud(
        width=1600,
        height=800,
        background_color="white",
        stopwords=custom_stopwords
    ).generate(text)

    # Create the figure and display the wordcloud image
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")

    # Save the wordcloud image with a high DPI for better resolution
    plt.savefig(wordcloud_path, dpi=500, bbox_inches="tight")
    print(f"Wordcloud saved as {wordcloud_path}")


def get_files_yearly_counts_for_origin(session: Session, origin_name: str):
    stmt = (
        select(
            extract('year', Dataset.date_created).label('year'),
            func.count(Dataset.dataset_id).label('count')
        )
        .join(File, File.dataset_id == Dataset.dataset_id)
        .join(DatasetOrigin, Dataset.origin_id == DatasetOrigin.origin_id)
        .where(DatasetOrigin.name == origin_name)
        .group_by('year')
        .order_by('year')
    )
    results = session.exec(stmt).all()
    return {int(row.year): row.count for row in results if row.year is not None}


def create_files_plot():
    with Session(engine) as session:
        zenodo_data = get_files_yearly_counts_for_origin(session, "zenodo")
        osf_data = get_files_yearly_counts_for_origin(session, "osf")
        figshare_data = get_files_yearly_counts_for_origin(session, "figshare")

    all_years = sorted(
        set(zenodo_data.keys()) | set(osf_data.keys()) | set(figshare_data.keys())
    )

    data = {
        'year': [str(y) for y in all_years],
        'Zenodo': [zenodo_data.get(y, 0) for y in all_years],
        'OSF': [osf_data.get(y, 0) for y in all_years],
        'Figshare': [figshare_data.get(y, 0) for y in all_years]
    }

    source = ColumnDataSource(data=data)
    repositories = ["Zenodo", "OSF", "Figshare"]
    colors = ['#66c2a5', '#fc8d62', '#8da0cb']

    p = figure(
        x_range=data['year'],
        height=500,
        width=800,
        title="Number of files per year per data repository",
        tooltips=[
            ("Year", "@year"),
            ("Data repository", "$name"),
            ("Number of files", "@$name{0,0}")
        ],
        background_fill_color="#fafafa",
    )

    p.toolbar.active_drag = None

    p.vbar_stack(
        stackers=repositories,
        x='year',
        width=0.8,
        source=source,
        color=colors,
        legend_label=repositories
    )
    p.xaxis.axis_label = "Year"
    p.yaxis.axis_label = "Number of files"

    p.title.text_font_size = "14pt"
    p.xaxis.axis_label_text_font_size = "12pt"
    p.yaxis.axis_label_text_font_size = "12pt"
    p.xaxis.major_label_text_font_size = "10pt"
    p.yaxis.major_label_text_font_size = "10pt"

    p.legend.location = "top_left"
    p.legend.background_fill_alpha = 0.3
    p.legend.border_line_color = None
    p.legend.label_text_font_size = "10pt"

    return p


# Similarly, create a plot for datasets per year.
def get_dataset_yearly_counts_for_origin(session: Session, origin_name: str):
    stmt = (
        select(
            extract('year', Dataset.date_created).label('year'),
            func.count(Dataset.dataset_id).label('count')
        )
        .join(DatasetOrigin, Dataset.origin_id == DatasetOrigin.origin_id)
        .where(DatasetOrigin.name == origin_name)
        .group_by('year')
        .order_by('year')
    )
    results = session.exec(stmt).all()
    return {int(row.year): row.count for row in results if row.year is not None}


def create_datasets_plot():
    with Session(engine) as session:
        zenodo_data = get_dataset_yearly_counts_for_origin(session, "zenodo")
        osf_data = get_dataset_yearly_counts_for_origin(session, "osf")
        figshare_data = get_dataset_yearly_counts_for_origin(session, "figshare")

    all_years = sorted(
        set(zenodo_data.keys()) | set(osf_data.keys()) | set(figshare_data.keys())
    )

    data = {
        'year': [str(y) for y in all_years],
        'Zenodo': [zenodo_data.get(y, 0) for y in all_years],
        'OSF': [osf_data.get(y, 0) for y in all_years],
        'Figshare': [figshare_data.get(y, 0) for y in all_years]
    }

    source = ColumnDataSource(data=data)
    repositories = ["Zenodo", "OSF", "Figshare"]
    colors = ['#66c2a5', '#fc8d62', '#8da0cb']

    p = figure(
        x_range=data['year'],
        height=500,
        width=800,
        title="Number of datasets per year per data repository",
        tooltips=[
            ("Year", "@year"),
            ("Data repository", "$name"),
            ("Number of datasets", "@$name{0,0}")
        ],
        background_fill_color="#fafafa",
    )

    p.toolbar.active_drag = None

    p.vbar_stack(
        stackers=repositories,
        x='year',
        width=0.8,
        source=source,
        color=colors,
        legend_label=repositories
    )
    p.xaxis.axis_label = "Year"
    p.yaxis.axis_label = "Number of datasets"

    p.title.text_font_size = "14pt"
    p.xaxis.axis_label_text_font_size = "12pt"
    p.yaxis.axis_label_text_font_size = "12pt"
    p.xaxis.major_label_text_font_size = "10pt"
    p.yaxis.major_label_text_font_size = "10pt"

    p.legend.location = "top_left"
    p.legend.background_fill_alpha = 0.3
    p.legend.border_line_color = None
    p.legend.label_text_font_size = "10pt"

    return p


# ============================================================================
# Queries for file_types.html
# ============================================================================


def get_file_type_stats():
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
            # .order_by(func.count(func.distinct(File.file_id)).desc())
            # order_by could be used to sort the results
            # by the number of files per file type
            # but it is not necessary for this example
            # because the template will sort the results
            # in the frontend using the DataTables options
        )

        file_type_stats_summary = session.exec(statement).all()

        return file_type_stats_summary


def get_tsv_depending_on_type(file_type: str) -> pd.DataFrame:
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

# ============================================================================
# Queries for search.html
# ============================================================================


def get_all_datasets() -> list[Dataset]:
    """
    Returns a list of all dataset objects, with their related objects loaded.
    """
    with Session(engine) as session:
        statement = (
            select(Dataset)
            .options(
                selectinload(Dataset.origin),
                selectinload(Dataset.author),
                selectinload(Dataset.keyword),
            )
        )
        results = session.exec(statement).all()
        return results


def get_dataset_info_by_id(dataset_id: int):
    """
    Returns dataset from its id.
    """
    with Session(engine) as session:
        statement_dataset = (
            select(Dataset)
            .options(
                # Load the related origin object so that dataset.origin is available.
                selectinload(Dataset.origin),
                # Load the many-to-many relationship for authors and keywords
                selectinload(Dataset.author),
                selectinload(Dataset.keyword)
            )
            .where(Dataset.dataset_id == dataset_id)
        )

        # Count how many total files, topology, parameter, and
        # trajectory files are in the dataset
        statement_total_files = (
            select(
            func.count(File.file_id).label("total_all_files"),
            func.count(File.file_id).filter(FileType.name == "gro").label("total_topology_files"),
            func.count(File.file_id).filter(FileType.name == "mdp").label("total_parameter_files"),
            func.count(File.file_id).filter(FileType.name == "xtc").label("total_trajectory_files"),
            )
            .join(FileType, File.file_type_id == FileType.file_type_id)
            .where(File.dataset_id == dataset_id)
        )

        # Count how many files have been analysed for this dataset,
        # a.k.a. how many are actually in the tables
        statement_analysed_files = select(
            (select(func.count(TopologyFile.file_id))
            .select_from(TopologyFile)
            .join(File, File.file_id == TopologyFile.file_id, isouter=True)
            .where(File.dataset_id == dataset_id)
            ).label("analysed_topology_files"),
            (select(func.count(ParameterFile.file_id))
            .select_from(ParameterFile)
            .join(File, File.file_id == ParameterFile.file_id, isouter=True)
            .where(File.dataset_id == dataset_id)
            ).label("analysed_parameter_files"),
            (select(func.count(TrajectoryFile.file_id))
            .select_from(TrajectoryFile)
            .join(File, File.file_id == TrajectoryFile.file_id, isouter=True)
            .where(File.dataset_id == dataset_id)
            ).label("analysed_trajectory_files")
        )

        result_dataset = session.exec(statement_dataset).first()
        result_total_files = session.exec(statement_total_files).first()
        result_analysed_files = session.exec(statement_analysed_files).first()

        return result_dataset, result_total_files, result_analysed_files


# ============================================================================
# Queries for dataset_file_info.html
# ============================================================================


def get_all_files_from_dataset(dataset_id: int) -> list[File]:
    """
    Returns a list of all files for a given dataset_id.
    """
    with Session(engine) as session:
        statement = (
            select(File)
            .options(
                selectinload(File.file_type),
                selectinload(File.dataset),
            )
            .where(File.dataset_id == dataset_id)
        )
        results = session.exec(statement).all()
        return results


def get_top_files(
        dataset_id: int | None = None,
        sort_column_name: str | None = None,
        sort_direction: str | None = "asc",
        start: int | None = None,
        length: int | None = None,
        search: str | None = None,
    ) -> list[TopologyFile]:
    """
    Returns a list of topology files with their related File, Dataset, and Dataset.origin info.
    
    If a dataset_id is provided, only topology files for that dataset are returned.
    Otherwise, all topology files are returned.
    """

    statement = (
        select(
            TopologyFile.atom_number.label("atom_number"),
            TopologyFile.has_protein.label("has_protein"),
            TopologyFile.has_nucleic.label("has_nucleic"),
            TopologyFile.has_lipid.label("has_lipid"),
            TopologyFile.has_glucid.label("has_glucid"),
            TopologyFile.has_water_ion.label("has_water_ion"),
            File.name.label("file_name"),
            Dataset.id_in_origin.label("dataset_id_in_origin"),
            Dataset.url.label("dataset_url"),
            DatasetOrigin.name.label("dataset_origin"),
        )
        .join(File, TopologyFile.file_id == File.file_id)
        .join(Dataset, File.dataset_id == Dataset.dataset_id)
        .join(DatasetOrigin, Dataset.origin_id == DatasetOrigin.origin_id)
    )

    if dataset_id is not None:
        statement = statement.where(TopologyFile.file.has(File.dataset_id == dataset_id))

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
            File.name.ilike(f"%{search}%"),
            TopologyFile.atom_number.ilike(f"%{search}%"),
            TopologyFile.has_protein.ilike(f"%{search}%"),
            TopologyFile.has_nucleic.ilike(f"%{search}%"),
            TopologyFile.has_lipid.ilike(f"%{search}%"),
            TopologyFile.has_glucid.ilike(f"%{search}%"),
            TopologyFile.has_water_ion.ilike(f"%{search}%")
        ))

    with Session(engine) as session:
        results = session.exec(statement).all()
        
        return results


def get_param_files(dataset_id: Optional[int] = None) -> list[ParameterFile]:
    """
    Returns a list of all parameter files with their related File, Dataset, and Dataset.origin info,
    as well as related Barostat, Integrator, and Thermostat info.
    
    If a dataset_id is provided, only parameter files for that dataset are returned.
    """

    statement = (
        select(
            ParameterFile,
            File.name.label("file_name"),
            Dataset.id_in_origin.label("dataset_id_in_origin"),
            Dataset.url.label("dataset_url"),
            DatasetOrigin.name.label("dataset_origin"),
            Barostat.name.label("barostat_name"),
            Integrator.name.label("integrator_name"),
            Thermostat.name.label("thermostat_name"),
        )
        .join(File, ParameterFile.file_id == File.file_id)
        .join(Dataset, File.dataset_id == Dataset.dataset_id)
        .join(DatasetOrigin, Dataset.origin_id == DatasetOrigin.origin_id)
        .outerjoin(Barostat, ParameterFile.barostat_id == Barostat.barostat_id)
        .outerjoin(Integrator, ParameterFile.integrator_id == Integrator.integrator_id)
        .outerjoin(Thermostat, ParameterFile.thermostat_id == Thermostat.thermostat_id)
    )
    
    if dataset_id is not None:
        # Filter based on the dataset_id from the related File.
        statement = statement.where(ParameterFile.file.has(File.dataset_id == dataset_id))
    
    with Session(engine) as session:
        results = session.exec(statement).all()

        return results


def get_traj_files(dataset_id: Optional[int] = None) -> list[TrajectoryFile]:
    """
    Returns a list of all trajectory files with their related File, Dataset, and Dataset.origin info.
    
    If a dataset_id is provided, only parameter files for that dataset are returned.
    """
    with Session(engine) as session:
        statement = (
            select(TrajectoryFile)
            .options(
                selectinload(TrajectoryFile.file)
                    .selectinload(File.dataset)
                    .selectinload(Dataset.origin),
            )
        )
        
        if dataset_id is not None:
            statement = statement.where(TrajectoryFile.file.has(File.dataset_id == dataset_id))
    
        with Session(engine) as session:
            results = session.exec(statement).all()
            return results