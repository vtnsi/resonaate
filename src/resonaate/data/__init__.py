# Third Party Imports
from sqlalchemy.ext.declarative import declarative_base

## Base declarative class used by SQLAlchemy to track ORM's
Base = declarative_base()  # pylint: disable=invalid-name


class _DataMixin:
    """Base class for objects that get stored via SQLAlchemy."""

    MUTABLE_COLUMN_NAMES = tuple()
    """tuple: Tuple of mutable column names."""

    def __repr__(self):
        """Define how :class:`.DataMixin` objects are represented as a ``str`` object.

        Returns:
            str: String representation of this :class:`.DataMixin` object.
        """
        if self.__class__.__name__ == "Agent":
            rep_str = "{0}(".format(self.__class__)
        else:
            rep_str = "{0}(id={1}, ".format(self.__class__, self.id)
        for field in self.MUTABLE_COLUMN_NAMES:
            rep_str += "{0}={1}, ".format(field, getattr(self, field))
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
            raise TypeError("Can't compare {0} object to {1} object.".format(type(self), type(other)))

        # False if any of the columns aren't equal
        for attribute in self.MUTABLE_COLUMN_NAMES:
            if getattr(self, attribute) != getattr(other, attribute):
                return False

        return True

    def makeDictionary(self):
        """Return a dictionary representation of this :class:`.DataMixin` object.

        Returns:
            dict: Dictionary representation of this :class:`.DataMixin` object.
        """
        retval = {}
        for field in self.MUTABLE_COLUMN_NAMES:
            retval[field] = getattr(self, field)

        return retval
