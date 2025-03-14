from pathlib import Path

import matplotlib.pyplot as plt
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from sqlalchemy import extract, func
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select
from wordcloud import STOPWORDS, WordCloud

from db_schema import (
    Dataset,
    DatasetKeywordLink,
    DatasetOrigin,
    File,
    FileType,
    Keyword,
    ParameterFile,
    TopologyFile,
    engine,
)

# ============================================================================
# Queries for index.html
# ============================================================================


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
            "First dataset": "nan",
            "Last dataset": "nan",
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


# def get_keywords():
#     with Session(engine) as session:
#         statement = (
#             select(Keyword.entry)
#             .join(DatasetKeywordLink)
#         )

#         keywords = session.exec(statement).all()
#     return keywords


# def generate_keyword_wordcloud():
#     wordcloud_path = Path("static/wordcloud.png")

#     # Check if the file already exists
#     if wordcloud_path.exists():
#         print("Wordcloud already exists, skipping generation.")
#         return

#     # Retrieve keywords using the query function
#     keywords = get_keywords()  # e.g. ['molecule', 'simulation', 'protein', ...]

#     # Join all keywords into a single string (space separated)
#     text = " ".join(keywords)

#     # Define custom stopwords to remove unwanted words
#     custom_stopwords = set(STOPWORDS)
#     custom_stopwords.update(["none"])

#     # Create the WordCloud object
#     wordcloud = WordCloud(
#         width=1600,
#         height=800,
#         background_color="white",
#         stopwords=custom_stopwords
#     ).generate(text)

#     # Create the figure
#     plt.figure(figsize=(10, 5))
#     plt.imshow(wordcloud, interpolation="bilinear")
#     plt.axis("off")

#     # Save the wordcloud image
#     plt.savefig(wordcloud_path, dpi=500, bbox_inches="tight")
#     print(f"Wordcloud saved as {wordcloud_path}")

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


def get_dataset_by_id(dataset_id: int):
    """
    Returns dataset from its id.
    """
    with Session(engine) as session:
        statement = (
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
        result = session.exec(statement).first()
        return result


# ============================================================================
# Queries for gro_files.html
# ============================================================================

def get_gro_files_info() -> list[TopologyFile]:
    pass

# ============================================================================
# Queries for mdp_files.html
# ============================================================================

def get_mdp_files_info() -> list[ParameterFile]:
    """
    Returns a list of all parameter files. The relationships to the tables
    Barostat, Integrator, and Thermostat are loaded as well.
    """
    with Session(engine) as session:
        statement = (
            select(ParameterFile)
            .options(
                selectinload(ParameterFile.file),
                selectinload(ParameterFile.barostat),
                selectinload(ParameterFile.integrator),
                selectinload(ParameterFile.thermostat),
            )
        )
        results = session.exec(statement).all()
        return results