"""Functions for extra processing of the Resonaate service layer output."""
# RESONAATE Imports
from resonaate.data.ephemeris import EstimateEphemeris
from resonaate.data.observation import Observation
from resonaate.physics.time.stardate import JulianDate

MERGE_LIST = [
    {
        "leader": 11111,
        "follower": 11112,
        "start_merge": 2458454.0006944444,
        "end_merge": 2458454.8026684606,
    },
]
"""list: List of dictionaries defining when docks (merges) take place between.

Each merge has the following fields defined:
    leader (int): Unique ID of RSO who's output is used for each docking (follower) RSO.
    follower (int): Unique ID of RSO that's docked with the leader RSO.
    start_merge (float): Julian date of when to merge the outputs of the docking RSOs.
    end_merge (float): Julian date of when to stop mergin the outputs of the docking RSOs.
"""


MERGE_LIST_INDEX = len(MERGE_LIST)
"""``int``: total number of merges to process."""


DOCKING_SATS = {11111, 11112}
"""set: Set of unique RSO identifiers present in the MERGE_LIST.

This set is helpful in determining whether the merge list needs to be searched for a particular
unique RSO ID.
"""


def determineCurrentLeader(sat_num, current_julian_time, merge_list_index=MERGE_LIST_INDEX):
    """Follow recursion based on order of ``MERGE_LIST`` to determine real leader.

    Args:
        sat_num (int): Unique ID of RSO to find leader for.
        current_julian_time (float,JulianDate): Current date/time in Julian date format.
        merge_list_index (int,optional): How far down the ``MERGE_LIST`` to go.

    Returns:
        int: Return leader of sat_num. If sat_num has no leader, sat_num will be returned.
    """
    if sat_num not in DOCKING_SATS:
        return sat_num

    leader = None
    end = 0
    for ii, merge in enumerate(MERGE_LIST):
        end = ii
        conditions = (
            merge["follower"] == sat_num,
            current_julian_time >= merge["start_merge"],
            current_julian_time < merge["end_merge"],
        )
        if all(conditions):
            leader = merge["leader"]
            break

        if ii > merge_list_index:
            break

    if leader is None:
        # got through relevant part of list and couldn't find a leader
        return sat_num
    # else
    return determineCurrentLeader(leader, current_julian_time, merge_list_index=end)


def isLeader(sat_num, current_julian_time):
    """Determine if RSO is currently a 'leader' in a docking pair.

    This method will only return `True` if a satellite is a determined leader. I.e. in an "a"
    follows "b" follows "c" situation, only "c" will return `True` for this method.

    Args:
        sat_num (int): Unique ID of RSO to determine leader status for.
        current_julian_time (float,JulianDate): Current date/time in Julian date format.

    Returns:
        bool: Indication of whether RSO is currently a leader in a docking pair.
    """
    if sat_num not in DOCKING_SATS:
        return False

    leader_merge = None
    for merge in MERGE_LIST:
        conditions = (
            merge["leader"] == sat_num,
            current_julian_time >= merge["start_merge"],
            current_julian_time < merge["end_merge"],
        )
        if all(conditions):
            leader_merge = merge
            break

    if leader_merge is None:
        return False
    # else
    return determineCurrentLeader(sat_num, current_julian_time) == sat_num


class LostRSO:
    """Abstract the functionality of an RSO that is lost and/or becomes uncorrelated."""

    def __init__(
        self,
        sat_num,
        time_lost,
        time_found,
        time_uncorrelated=None,
        uncorrelated_sat_num=None,
        uncorrelated_sat_name=None,
    ):
        """Instantiate a new :class:`.LostRSO` based on parameters.

        Args:
            sat_num (int): Original satellite number of missing RSO.
            time_lost (JulianDate): Time to start not publishing estimates / observations for RSO.
            time_found (JulianDate): Time to start publishing estimates / observations for RSO (with
                correct sat_num and sat_name).
            time_uncorrelated (JulianDate,optional): Time to start publishing estimates /
                with uncorrelated_sat_num and uncorrelated_sat_name identifiers.
            uncorrelated_sat_num (int): Satellite number to use in output from time_uncorrelated to
                time_found.
            uncorrelated_sat_name (str): Satellite name to use in output from time_uncorrelated to
                time_found.
        """
        self._sat_num = sat_num
        if not isinstance(self._sat_num, int):
            err = f"Satellite number must be an int, not '{type(self._sat_num)}'"
            raise TypeError(err)

        self._time_lost = time_lost
        if not isinstance(self._time_lost, JulianDate):
            err = f"Time lost must be a JulianDate, not '{type(self._time_lost)}'"
            raise TypeError(err)

        self._time_found = time_found
        if not isinstance(self._time_found, JulianDate):
            err = f"Time found must be a JulianDate, not '{type(self._time_found)}'"
            raise TypeError(err)

        self._time_uncorrelated = time_uncorrelated
        self._uncorrelated_sat_num = uncorrelated_sat_num
        self._uncorrelated_sat_name = uncorrelated_sat_name

        if self._time_uncorrelated is not None:
            self._time_found = time_found
            if not isinstance(self._time_uncorrelated, JulianDate):
                err = f"Time uncorrelated must be a JulianDate, not '{type(self._time_uncorrelated)}'"
                raise TypeError(err)

            if self._uncorrelated_sat_num is None or self._uncorrelated_sat_name is None:
                err = (
                    f"If satellite becomes uncorrelated at {self._time_uncorrelated},"
                    + " please provide uncorrelated name and number."
                )
                raise ValueError(err)

            if not isinstance(self._uncorrelated_sat_num, int):
                err = f"Uncorrelated satellite number must be an int, not '{type(self._uncorrelated_sat_num)}'"
                raise TypeError(err)

            if not isinstance(self._uncorrelated_sat_name, str):
                err = f"Uncorrelated satellite name must be a str, not '{type(self._uncorrelated_sat_name)}'"
                raise TypeError(err)

    def isLost(self, current_julian_time):
        """Return boolean indicating whether this satellite is currently lost.

        Args:
            current_julian_time (JulianDate): Current date/time in Julian date format.

        Returns:
            bool: Indication of whether this satellite is currently lost.
        """
        if not isinstance(current_julian_time, JulianDate):
            err = f"Current Julian time must be a JulianDate, not '{type(current_julian_time)}'"
            raise TypeError(err)

        end_lost = self._time_found
        if self._time_uncorrelated is not None:
            end_lost = self._time_uncorrelated

        return self._time_lost <= current_julian_time < end_lost

    def isUncorrelated(self, current_julian_time):
        """Return boolean indicating of whether this satellite is currently uncorrelated.

        Args:
            current_julian_time (JulianDate): Current date/time in Julian date format.

        Returns:
            bool: Indication of whether this satellite is currently uncorrelated.
        """
        if self._time_uncorrelated is None:
            return False

        return self._time_uncorrelated <= current_julian_time < self._time_found

    def uncorrelateOutput(self, data_obj):
        """Replace the `id` and `name` fields in data_obj to uncorrelated values.

        Args:
            data_obj (:class:`.EstimateEphemeris` | :class:`.Observation`): Estimate or Observation
                data dictionary to uncorrelate.
        """
        if isinstance(data_obj, EstimateEphemeris):
            data_obj.agent_id = self._uncorrelated_sat_num
            data_obj.name = self._uncorrelated_sat_name
        elif isinstance(data_obj, Observation):
            data_obj.target_id = self._uncorrelated_sat_num
            data_obj.target_name = self._uncorrelated_sat_name
        else:
            raise TypeError(type(data_obj))

        return data_obj


LOST_UCT_TARGETS = {
    11113: LostRSO(
        11113,
        JulianDate.getJulianDate(2018, 12, 1, 12, 1, 0),
        JulianDate.getJulianDate(2018, 12, 1, 12, 30, 0),
        time_uncorrelated=JulianDate.getJulianDate(2018, 12, 1, 12, 20, 0),
        uncorrelated_sat_num=90001,
        uncorrelated_sat_name="UCT-1",
    ),
}


def isLostOrUncorrelated(sat_num, current_julian_time):
    """Determine if a satellite is currently lost or uncorrelated.

    Args:
        sat_num (int): Satellite number of relevant RSO.
        current_julian_time (JulianDate): Current date/time in Julian date format.

    Return:
        bool: Indication of whether a satellite is either lost or uncorrelated.
    """
    lost_rso = LOST_UCT_TARGETS.get(sat_num)
    if lost_rso is not None:
        return lost_rso.isLost(current_julian_time) or lost_rso.isUncorrelated(current_julian_time)
    # else
    return False


def mungeLostUCTData(data_obj):
    """Update fields of a database object based on state of RSO.

    For RSO's that aren't currently lost or uncorrelated, data_obj will be returned. For
    uncorrelated RSO's, identifiers 'satName' and 'satNum' in data_obj will be replaced with
    uncorrelated identifiers. If the RSO is currently in a lost state, then `None` will be returned.

    Args:
        data_obj (:class:`.EstimateEphemeris`|:class:`.Observation`): object where data may need to be munged.

    Returns:
        :class:`.EstimateEphemeris`|:class:`.Observation`|None: Potentially munged data or `None`.
    """
    current_julian_time = JulianDate(data_obj.julian_date)

    if isinstance(data_obj, EstimateEphemeris):
        sat_num = data_obj.agent_id
    elif isinstance(data_obj, Observation):
        sat_num = data_obj.target_id
    else:
        raise TypeError(type(data_obj))

    if isLostOrUncorrelated(sat_num, current_julian_time):
        lost_rso = LOST_UCT_TARGETS[sat_num]
        if lost_rso.isLost(current_julian_time):
            return None
        if lost_rso.isUncorrelated(current_julian_time):
            return lost_rso.uncorrelateOutput(data_obj)
    # else
    return data_obj
