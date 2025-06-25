"""Defines the declarative base for data tables."""

from __future__ import annotations

# Third Party Imports
from sqlalchemy.orm import declarative_base


class _Base:
    """Dummy class to allow for type hints without Mapped[] until we enforce SQLAlchemy >= 2.0."""

    # [NOTE]: See https://docs.sqlalchemy.org/en/20/changelog/migration_20.html#migration-to-2-0-step-four-use-the-future-flag-on-engine
    # __allow_unmapped__ doesn't seem to function as intended. Ended up type hinting with Mapped instead.
    __allow_unmapped__ = True


# Base declarative class used by SQLAlchemy to track ORM's
Base = declarative_base(cls=_Base)


class _DataMixin:
    """Base class for objects that get stored via SQLAlchemy."""

    MUTABLE_COLUMN_NAMES = ()
    """tuple: Tuple of mutable column names."""

    def __repr__(self):
        """Define how :class:`.DataMixin` objects are represented as a ``str`` object.

        Returns:
            str: String representation of this :class:`.DataMixin` object.
        """
        if self.__class__.__name__ == "AgentModel":
            rep_str = f"{self.__class__}("
        else:
            rep_str = f"{self.__class__}(id={self.id}, "
        for field in self.MUTABLE_COLUMN_NAMES:
            rep_str += f"{field}={getattr(self, field)}, "
        rep_str += ")"

        return rep_str

    def __eq__(self, other):
        """Define how :class:`.DataMixin` objects can be compared to other objects (i.e. `==`, `!=`).

        Args:
            other (object): Object to compare this :class:`.DataMixin` object to.

        Returns:
            bool: Indicates if the two objects are equal.
        """
        if not isinstance(self, other.__class__):
            raise TypeError(f"Can't compare {type(self)} object to {type(other)} object.")

        return not any(
            getattr(self, attr) != getattr(other, attr) for attr in self.MUTABLE_COLUMN_NAMES
        )

    def makeDictionary(self) -> dict:
        """Return a dictionary representation of this :class:`.DataMixin` object.

        Returns:
            dict: Dictionary representation of this :class:`.DataMixin` object.
        """
        retval = {}
        for field in self.MUTABLE_COLUMN_NAMES:
            retval[field] = getattr(self, field)

        return retval
