"""Defines functions for common queries as well as functions that augment queries."""

from __future__ import annotations

# Third Party Imports
from numpy import around


def addAlmostEqualFilter(query, data_type, field, value, decimal_places=6):
    """Add a `::filter()` call to given :class:`.Query` to results that almost equal a given value.

    Args:
        query (`sqlalchemy.orm.Query`): Query object to add the filter to
        data_type (`._DataMixin`): type of data to be pulling from the database
        field (str): name of column to use
        value (float): value to be almost equal to
        decimal_places (int): number of decimal places to round to

    Returns:
        `sqlalchemy.orm.Query`: given query with `::filter()` called on it to apply "almost equal"
    """
    rounded_target = float(around(value, decimals=decimal_places))
    delta = 1 * pow(10, (-1 * decimal_places))
    upper_bound = rounded_target + delta
    lower_bound = rounded_target - delta

    return query.filter(
        getattr(data_type, field) < upper_bound,
        getattr(data_type, field) > lower_bound,
    )
