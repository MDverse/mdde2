from sqlalchemy import func, extract
from sqlalchemy.orm import selectinload
from pathlib import Path
from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource
from bokeh.io import save, output_file

from sqlmodel import Session, select

from db_schema import engine
from db_schema import Dataset, DatasetOrigin, File, FileType, Keyword, DatasetKeywordLink

from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt

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

def get_all_datasets():
    """
    Returns a list of all dataset objects, with their related objects loaded.
    """
    with Session(engine) as session:
        statement = select(Dataset).options(
            # Load the related origin object so that dataset.origin is available.
            selectinload(Dataset.origin),
            # Load the many-to-many relationship for authors and keywords
            selectinload(Dataset.author),
            selectinload(Dataset.keyword)
        )
        results = session.exec(statement).all()
        return results


def get_keywords():
    with Session(engine) as session:
        statement = (
            select(Keyword.entry)
            .join(DatasetKeywordLink)
        )

        keywords = session.exec(statement).all()
    return keywords


def generate_keyword_wordcloud():
    wordcloud_path = Path("static/wordcloud.png")
    
    # Check if the file already exists
    if wordcloud_path.exists():
        print("Wordcloud already exists, skipping generation.")
        return

    # Retrieve keywords using the query function
    keywords = get_keywords()  # e.g. ['molecule', 'simulation', 'protein', ...]
    
    # Join all keywords into a single string (space separated)
    text = " ".join(keywords)
    
    # Define custom stopwords to remove unwanted words
    custom_stopwords = set(STOPWORDS)
    custom_stopwords.update(["none"])

    # Create the WordCloud object
    wordcloud = WordCloud(
        width=1600,
        height=800,
        background_color="white",
        stopwords=custom_stopwords
    ).generate(text)

    # Create the figure
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    
    # Save the wordcloud image
    plt.savefig(wordcloud_path, dpi=500)
    print(f"Wordcloud saved as {wordcloud_path}")


def get_yearly_counts_for_origin(session: Session, origin_name: str):
    """
    Return a dict mapping year -> count of Datasets for the given origin_name.
    """
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
    # Convert list of tuples to dict {year: count}
    return {int(row.year): row.count for row in results if row.year is not None}

def create_bokey_plot():
    with Session(engine) as session:
        zenodo_data = get_yearly_counts_for_origin(session, "zenodo")
        osf_data = get_yearly_counts_for_origin(session, "osf")
        figshare_data = get_yearly_counts_for_origin(session, "figshare")

    all_years = sorted(list(
        set(zenodo_data.keys()) | set(osf_data.keys()) | set(figshare_data.keys())
    ))

    data = {
        'year': [str(y) for y in all_years],
        'Zenodo': [zenodo_data.get(y, 0) for y in all_years],
        'OSF': [osf_data.get(y, 0) for y in all_years],
        'Figshare': [figshare_data.get(y, 0) for y in all_years]
    }

    source = ColumnDataSource(data=data)

    repositories = ["Zenodo", "OSF", "Figshare"]
    colors = ["#2055A5", "#E3712B", "#7C1533"]

    p = figure(
        x_range=data['year'],
        plot_height=500,
        plot_width=700,
        title="Number of files per year per data repository",
        toolbar_location=None,
        tools="hover",
        tooltips="@year: @$name"
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
    p.xaxis.major_label_orientation = 0  # 0 means horizontal text
    p.legend.location = "top_left"

    # Save and/or show
    output_file("files_by_year.html")
    save(p)  # saves the plot to files_by_year.html
    show(p)  # opens the plot in a browser
