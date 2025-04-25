from pathlib import Path

import time
from datetime import timedelta

import pandas as pd
from sqlalchemy import extract, func, case, desc
from sqlalchemy.orm import selectinload, aliased
from sqlmodel import Session, select, or_, col
from typing import Optional

from ..db_schema import (
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
# Queries for dataset_file_info.html
# ============================================================================





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