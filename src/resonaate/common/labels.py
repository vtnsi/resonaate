"""Hold common label types for easier importing."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Literal

ECI_LABEL: Literal = "eci"
COE_LABEL: Literal = "coe"
EQE_LABEL: Literal = "eqe"
LLA_LABEL: Literal = "lla"
