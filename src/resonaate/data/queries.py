"""This module contains functions that execute common database queries for post-processing RESONAATE data."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from sqlalchemy import asc, distinct
from sqlalchemy.orm import Query

# Local Imports
from ..common.logger import resonaateLogError
from ..physics.time.stardate import JulianDate
from .agent import AgentModel
from .ephemeris import EstimateEphemeris, TruthEphemeris
from .observation import Observation

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Sequence

    # Local Imports
    from .data_interface import DataInterface


def fetchAgentIDs(database: DataInterface) -> list[int]:
    """Fetches list of agent IDs of all agents present in scenario.

    Notes:
        Having distinct in the query returns a tuple, so `sat_num_list_sql`
        is a list of one-length tuples: `[(item0, ), (item1, ), ..., (itemN, )]`.

    Args:
        database (:class:`.DataInterface`): Data interface object associated with a database

    Returns:
        (``list``): list of agent ID numbers, as integers
    """
    agent_id_tuples = database.getData(Query(distinct(AgentModel.unique_id)), multi=True)
    return [int(agent_id_tuple[0]) for agent_id_tuple in agent_id_tuples]


def fetchEstimateIDs(database: DataInterface) -> list[int]:
    """Fetches list of estimate agent IDs of all agents present in scenario.

    Notes:
        Having distinct in the query returns a tuple, so `sat_num_list_sql`
        is a list of one-length tuples: `[(item0, ), (item1, ), ..., (itemN, )]`.

    Args:
        database (:class:`.DataInterface`): Data interface object associated with a database

    Returns:
        (``list``): list of estimate agent ID numbers, as integers
    """
    est_agent_id_tuples = database.getData(Query(distinct(EstimateEphemeris.agent_id)), multi=True)
    return [int(agent_id_tuple[0]) for agent_id_tuple in est_agent_id_tuples]


def fetchEstimatesByJDInterval(
    database: DataInterface,
    sat_nums: Sequence[int],
    jd_lb: JulianDate | None = None,
    jd_ub: JulianDate | None = None,
) -> list[EstimateEphemeris]:
    """Get a posteriori estimate states of a specific target.

    Args:
        database (:class:`.DataInterface`): Data interface object associated with a database
        sat_nums (``Sequence``): estimate IDs corresponding to desired data
        jd_lb (:class:`.JulianDate` | None): lower bound on Julian date for query. Defaults to `None`.
        If `None`, all timesteps before `jd_ub` will be returned
        jd_ub (:class:`.JulianDate` | None): upper bound on Julian date for query. Defaults to `None`.
        If `None`, all timesteps after `jd_lb` will be returned

    Returns:
        (``list``): list of :class:.EstimateEphemeris objects
    """
    return database.getData(jdIntervalQuery(EstimateEphemeris, "agent_id", sat_nums, jd_lb, jd_ub))


def fetchEstimatesByJDEpoch(
    database: DataInterface,
    sat_nums: Sequence[int],
    jd: JulianDate,
) -> list[EstimateEphemeris]:
    """Get a posteriori estimate states during a specific time.

    Args:
        database (:class:`.DataInterface`): Data interface object associated with a database
        sat_nums (``Sequence``): estimate IDs corresponding to desired data
        jd (:class:`.JulianDate`): Julian Date epoch to fetch data for `sat_nums`

    Returns:
        (``list``): list of :class:`Observation` objects
    """
    return database.getData(jdEpochQuery(EstimateEphemeris, "agent_id", sat_nums, jd))


def fetchTruthByJDInterval(
    database: DataInterface,
    sat_nums: Sequence[int],
    jd_lb: JulianDate | None = None,
    jd_ub: JulianDate | None = None,
) -> list[TruthEphemeris]:
    """Get truth states of a specific target.

    Args:
        database (:class:`.DataInterface`): Data interface object associated with a database
        sat_nums (``Sequence``): estimate IDs corresponding to desired data
        jd_lb (:class:`.JulianDate` | None): lower bound on Julian date for query. Defaults to `None`.
        If `None`, all timesteps before `jd_ub` will be returned
        jd_ub (:class:`.JulianDate` | None): upper bound on Julian date for query. Defaults to `None`.
        If `None`, all timesteps after `jd_lb` will be returned

    Returns:
        (``list``): list of :class:`TruthEphemeris` objects
    """
    return database.getData(jdIntervalQuery(TruthEphemeris, "agent_id", sat_nums, jd_lb, jd_ub))


def fetchTruthByJDEpoch(
    database: DataInterface,
    sat_nums: Sequence[int],
    jd: JulianDate,
) -> list[TruthEphemeris]:
    """Get truth during a specific time.

    Args:
        database (:class:`.DataInterface`): Data interface object associated with a database
        sat_nums (``Sequence``): estimate IDs corresponding to desired data
        jd (:class:`.JulianDate`): Julian Date epoch to fetch data for `sat_nums`

    Returns:
        (``list``): list of :class:`Observation` objects
    """
    return database.getData(jdEpochQuery(TruthEphemeris, "agent_id", sat_nums, jd))


def fetchObservationsByJDInterval(
    database: DataInterface,
    sat_nums: Sequence[int],
    jd_lb: JulianDate | None = None,
    jd_ub: JulianDate | None = None,
) -> list[Observation]:
    """Get observations of a specific target.

    Args:
        database (:class:`.DataInterface`): Data interface object associated with a database
        sat_nums (``Sequence``): estimate IDs corresponding to desired data
        jd_lb (:class:`.JulianDate` | None): lower bound on Julian date for query. Defaults to `None`.
        If `None`, all timesteps before `jd_ub` will be returned
        jd_ub (:class:`.JulianDate` | None): upper bound on Julian date for query. Defaults to `None`.
        If `None`, all timesteps after `jd_lb` will be returned

    Returns:
        (``list``): list of :class:`Observation` objects
    """
    return database.getData(jdIntervalQuery(Observation, "target_id", sat_nums, jd_lb, jd_ub))


def fetchObservationsByJDEpoch(
    database: DataInterface,
    sat_nums: Sequence[int],
    jd: JulianDate,
) -> list[Observation]:
    """Get observations during a specific time.

    Args:
        database (:class:`.DataInterface`): Data interface object associated with a database
        sat_nums (``Sequence``): estimate IDs corresponding to desired data
        jd (:class:`.JulianDate`): Julian Date epoch to fetch data for `sat_nums`

    Returns:
        (``list``): list of :class:`Observation` objects
    """
    return database.getData(jdEpochQuery(Observation, "target_id", sat_nums, jd))


def jdIntervalQuery(
    table: EstimateEphemeris | TruthEphemeris | Observation,
    target_column: str,
    sat_nums: Sequence[int],
    jd_lb: JulianDate | None = None,
    jd_ub: JulianDate | None = None,
) -> Query:
    """Properly formats a generic database table query where bounds on Julian dates may not be defined.

    Args:
        table (:class:`.EstimateEphemeris` | :class:`.TruthEphemeris` | :class:`.Observation`): data table to query
        target_column (``str``): name of table column containing ID of target
        sat_nums (``Sequence``): estimate IDs corresponding to desired data
        jd_lb (:class:`.JulianDate` | None): lower bound on Julian date for query. Defaults to `None`.
        If `None`, all timesteps before `jd_ub` will be returned
        jd_ub (:class:`.JulianDate` | None): upper bound on Julian date for query. Defaults to `None`.
        If `None`, all timesteps after `jd_lb` will be returned

    Returns:
        (:class:`.Query`): Query object to retrieve data
    """
    if not jd_lb:
        jd_lb = JulianDate(0.0)
    if not jd_ub:
        jd_ub = JulianDate(float("inf"))
    query = Query(table).filter(getattr(table, target_column).in_(sat_nums))
    return filterByJulianDateInterval(query, table, jd_lb, jd_ub)


def jdEpochQuery(
    table: EstimateEphemeris | TruthEphemeris | Observation,
    target_column: str,
    sat_nums: Sequence[int],
    jd: JulianDate,
) -> Query:
    """Properly formats a generic database table query where single Julian date epoch is defined.

    Args:
        table (:class:`.EstimateEphemeris` | :class:`.TruthEphemeris` | :class:`.Observation`): data table to query
        target_column (``str``): name of table column containing ID of target
        sat_nums (``Sequence``): estimate IDs corresponding to desired data
        jd (:class:`.JulianDate`): Julian date for query

    Returns:
        (:class:`.Query`): Query object to retrieve data
    """
    query = Query(table).filter(getattr(table, target_column).in_(sat_nums))
    return filterBySingleJulianDate(query, table, jd)


def filterByJulianDateInterval(
    query: Query,
    table: EstimateEphemeris | TruthEphemeris | Observation,
    jd_lb: JulianDate,
    jd_ub: JulianDate,
) -> Query:
    """Generic framework for filtering satellite data query elapsing a range of time during a scenario.

    Args:
        query (``Query``): Query object to filter
        table (:class:`.EstimateEphemeris` | :class:`.TruthEphemeris` | :class:`.Observation`): data table to query
        jd_lb (:class:`.JulianDate`): lower bound on Julian date for query
        jd_ub (:class:`.JulianDate`): upper bound on Julian date for query

    Returns:
        (:class:`.Query`): Query object to retrieve data
    """
    if isinstance(jd_lb, JulianDate) and isinstance(jd_ub, JulianDate):
        if jd_lb > jd_ub:
            msg = "Julian date lower bound is greater than the upper bound"
            resonaateLogError(msg)
            raise ValueError(msg)
        return query.filter(table.julian_date.between(float(jd_lb), float(jd_ub))).order_by(
            asc(table.julian_date),
        )

    type_error_msg = "Julian date inputs must be type `.JulianDate`."
    resonaateLogError(type_error_msg)
    raise TypeError(type_error_msg)


def filterBySingleJulianDate(
    query: Query,
    table: EstimateEphemeris | TruthEphemeris | Observation,
    jd: JulianDate,
) -> Query:
    """Generic framework for filtering satellite data query at a single time during a scenario.

    Args:
        query (``Query``): Query object to filter
        table (:class:`.EstimateEphemeris`|:class:`.TruthEphemeris`|:class:`.Observation`): data table to query
        jd (:class:`.JulianDate`): single time of Julian date for query

    Returns:
        (:class:`Query`): Query object to retrieve data
    """
    type_error_msg: str = "Single Julian date must be type `Julian Date`, not type {0}!"
    if isinstance(jd, JulianDate):
        return query.filter(table.julian_date == float(jd))

    resonaateLogError(type_error_msg.format(type(jd)))
    raise TypeError(type_error_msg.format(type(jd)))
