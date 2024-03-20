from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from itertools import combinations, permutations

# Third Party Imports
import pytest
from numpy import array, eye, linspace
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.data import getDBConnection, setDBPath
from resonaate.data.agent import AgentModel
from resonaate.data.ephemeris import EstimateEphemeris, TruthEphemeris
from resonaate.data.epoch import Epoch
from resonaate.data.observation import Observation
from resonaate.data.queries import (
    fetchAgentIDs,
    fetchEstimateIDs,
    fetchEstimatesByJDEpoch,
    fetchEstimatesByJDInterval,
    fetchObservationsByJDEpoch,
    fetchObservationsByJDInterval,
    fetchTruthByJDEpoch,
    fetchTruthByJDInterval,
    filterByJulianDateInterval,
    filterBySingleJulianDate,
    jdEpochQuery,
    jdIntervalQuery,
)
from resonaate.data.resonaate_database import ResonaateDatabase
from resonaate.physics.constants import PI
from resonaate.physics.measurements import Measurement
from resonaate.physics.time.stardate import JulianDate

# SET UP RSO AGENTS
RSO_UNIQUE_IDS = [24601, 41914, 27839]
RSO_NAMES = ["Sat1", "Sat2", "Sat3"]
EXAMPLE_RSO = [{"name": name, "unique_id": uid} for name, uid in zip(RSO_NAMES, RSO_UNIQUE_IDS)]


# SET UP SENSOR AGENTS
SENSOR_UNIQUE_IDS = [1]
SENSOR_NAMES = ["Sensor1"]
EXAMPLE_SENSORS = [
    {"name": name, "unique_id": uid} for name, uid in zip(SENSOR_NAMES, SENSOR_UNIQUE_IDS)
]


# SET UP EPOCH ENTRIES
EXAMPLE_JD = [
    2458207.010416667,
    2459304.21527778,
    2459304.21875,
]
EXAMPLE_TIMESTAMPS = [
    "2019-01-01T00:01:00.000Z",
    "2021-03-30T17:10:00.000Z",
    "2021-03-30T17:15:00.000Z",
]
EXAMPLE_EPOCHS = [
    {"julian_date": jd, "timestampISO": ts} for jd, ts in zip(EXAMPLE_JD, EXAMPLE_TIMESTAMPS)
]


# SET UP TRUTH ENTRIES
RSO_TIMESTEPS = sorted(EXAMPLE_JD * len(EXAMPLE_RSO))
EXAMPLE_ECI_STATES = [
    [32832.44359, -26125.770428, -4175.978356, 1.920657, 2.399111, 0.090893],
    [2586.058936, 6348.302803, 3801.942400, -3.304773, -2.193913, 5.915754],
    [1296.645611, -2457.821083, 5721.873513, 0.179231, 0.093705, -0.000365],
    [32832.44359, -26125.770428, -4175.978356, 1.920657, 2.399111, 0.090893],
    [2586.058936, 6348.302803, 3801.942400, -3.304773, -2.193913, 5.915754],
    [1296.645611, -2457.821083, 5721.873513, 0.179231, 0.093705, -0.000365],
    [4642.213371, 41904.121624, -480.890384, -3.056102, 0.338368, -0.013438],
    [1909.774421, 6021.844998, -875.443327, -0.439119, 0.139392, 0.000890],
    [4087.816918, -2810.139684, 3995.864181, 0.204921, 0.297495, -0.000419],
]
EXAMPLE_TRUTH = [
    {"julian_date": jd, "agent_id": uid, "eci": eci}
    for jd, uid, eci in zip(RSO_TIMESTEPS, RSO_UNIQUE_IDS * 3, EXAMPLE_ECI_STATES)
]


# SET UP ESTIMATE ENTRIES
estimate_kwargs = {
    "covariance": eye(6),
    "source": "Observation",
}
EXAMPLE_ESTIMATES = [dict(ephem, **estimate_kwargs) for ephem in deepcopy(EXAMPLE_TRUTH)]


# SET UP OBSERVATION ENTRIES
azimuths = linspace(0, 2 * PI, num=len(EXAMPLE_RSO))
elevations = linspace(0, PI, num=len(EXAMPLE_RSO))
pos_x = [7000.0, 1.0, 2.0] * 3
pos_y = [0.5, 1.5, 2.5] * 3
pos_z = [0.0, 50.0, 100.0] * 3
vel_x = [2.0, 5.0, 7.0]
vel_y = [2.0, 5.0, 7.0]
vel_z = [2.0, 5.0, 7.0]
obs_vals = zip(
    RSO_TIMESTEPS,
    RSO_UNIQUE_IDS * 3,
    azimuths,
    elevations,
    pos_x,
    pos_y,
    pos_z,
    vel_x,
    vel_y,
    vel_z,
)
EXAMPLE_OBSERVATIONS = [
    {
        "julian_date": jd,
        "sensor_id": 1,
        "target_id": uid,
        "sensor_type": "Optical",
        "azimuth_rad": a_rad,
        "elevation_rad": e_rad,
        "sensor_eci": array([pos_x, pos_y, pos_z, vel_x, vel_y, vel_z]),
        "measurement": Measurement.fromMeasurementLabels(["azimuth_rad", "elevation_rad"], eye(2)),
    }
    for jd, uid, a_rad, e_rad, pos_x, pos_y, pos_z, vel_x, vel_y, vel_z in obs_vals
]


# SET UP POSSIBLE COMBINATIONS OF RSOS IN DATABASES
RSO_ID_COMBINATIONS = []
for iterator in [combinations(RSO_UNIQUE_IDS, n) for n in range(1, len(RSO_UNIQUE_IDS) + 1)]:
    for combination in iterator:
        RSO_ID_COMBINATIONS.append(combination)


# SET UP POSSIBLE JD QUERY BOUNDS
JD_LIST = [JulianDate(jd) for jd in EXAMPLE_JD]
JD_SPANS = [*permutations([*JD_LIST, None], 2)]
# prune from `JD_SPANS` where the lower bound is greater than the upper bound, for use later
BAD_JD_SPAN_BOUNDS = []
bad_span_idxs = []
for idx, span in enumerate(JD_SPANS):
    if isinstance(span[0], JulianDate) and isinstance(span[1], JulianDate) and span[0] > span[1]:
        bad_span_idxs.append(idx)
for bad_idx in reversed(bad_span_idxs):
    BAD_JD_SPAN_BOUNDS.append(JD_SPANS.pop(bad_idx))


@pytest.fixture(scope="module", name="agents")
def getMultipleAgents():
    """Create several valid :class:`.AgentModel` objects."""
    agents = []
    for rso in EXAMPLE_RSO:
        agents.append(AgentModel(**rso))
    for sensor in EXAMPLE_SENSORS:
        agents.append(AgentModel(**sensor))
    return agents


@pytest.fixture(scope="module", name="epochs")
def getMultipleEpochs():
    """Create several valid :class:`.Epoch` objects."""
    epochs = []
    for epoch in EXAMPLE_EPOCHS:
        epochs.append(Epoch(**epoch))
    return epochs


@pytest.fixture(scope="module", name="ephems")
def getMultipleEphemerisData():
    """Create several valid :class:`.TruthEphemeris` objects."""
    ephems = []
    for ex_ephem in EXAMPLE_TRUTH:
        ephems.append(TruthEphemeris.fromECIVector(**ex_ephem))
    return ephems


@pytest.fixture(scope="module", name="estimates")
def getMultipleEstimateData():
    """Create several valid :class:`.EstimateEphemeris` objects."""
    estimates = []
    for ex_estimate in EXAMPLE_ESTIMATES:
        estimates.append(EstimateEphemeris.fromCovarianceMatrix(**ex_estimate))
    return estimates


@pytest.fixture(scope="module", name="observations")
def getMultipleObservations():
    """Create several valid :class:`.Observation` objects."""
    observations = []
    for sensor_ob in EXAMPLE_OBSERVATIONS:
        observations.append(Observation(**sensor_ob))
    return observations


@pytest.fixture(scope="module", name="database")
def getDataInterface(agents, epochs, ephems, estimates, observations) -> ResonaateDatabase:
    """Create common, non-shared DB object for all tests.

    Yields:
        :class:`.ResonaateDatabase`: properly constructed DB object
    """
    # Create & yield instance.
    setDBPath("sqlite://")
    shared_interface = getDBConnection()
    shared_interface.bulkSave(deepcopy(agents + epochs + ephems + estimates + observations))
    yield shared_interface
    shared_interface.resetData(ResonaateDatabase.VALID_DATA_TYPES)


def testEstimateAgentIDs(database):
    """Test sat num query."""
    results = fetchEstimateIDs(database)
    assert results.sort() == RSO_UNIQUE_IDS.sort()


def testAllAgentIDs(database):
    """Test sat num query."""
    results = fetchAgentIDs(database)
    assert results.sort() == [RSO_UNIQUE_IDS + SENSOR_UNIQUE_IDS].sort()


INSERTED_DATA_FIXTURES = ["ephems", "estimates", "observations"]
TARGET_COLUMN_NAMES = ["agent_id", "agent_id", "target_id"]

INTERVAL_TEST_PARAMETERS = zip(
    [fetchTruthByJDInterval, fetchEstimatesByJDInterval, fetchObservationsByJDInterval],
    INSERTED_DATA_FIXTURES,
    TARGET_COLUMN_NAMES,
)


@pytest.mark.parametrize(("test_func", "fixture", "target_column"), INTERVAL_TEST_PARAMETERS)
@pytest.mark.parametrize("jd_span", JD_SPANS)
@pytest.mark.parametrize("rso", RSO_ID_COMBINATIONS)
def testIntervalFetches(test_func, fixture, target_column, database, rso, jd_span, request):
    """Test truth query at a span of Julian dates for a unique RSO."""
    fixture = request.getfixturevalue(fixture)
    jd_lb, jd_ub = jd_span
    results = test_func(database, rso, jd_lb, jd_ub)
    if not jd_lb:
        jd_lb = 0.0
    if not jd_ub:
        jd_ub = float("inf")
    correct_instances = []
    for instance in fixture:
        if (
            getattr(instance, target_column) in rso
            and instance.julian_date >= jd_lb
            and instance.julian_date <= jd_ub
        ):
            correct_instances.append(instance)
    ascending_rows = sorted(correct_instances, key=lambda d: d.julian_date)
    ascending_rows = sorted(ascending_rows, key=lambda d: getattr(d, target_column))
    ascending_results = sorted(results, key=lambda d: getattr(d, target_column))
    for result, correct_row in zip(ascending_results, ascending_rows):
        assert result == correct_row


EPOCH_TEST_PARAMETERS = zip(
    [fetchTruthByJDEpoch, fetchEstimatesByJDEpoch, fetchObservationsByJDEpoch],
    INSERTED_DATA_FIXTURES,
    TARGET_COLUMN_NAMES,
)


@pytest.mark.parametrize(("test_func", "table", "target_column"), deepcopy(EPOCH_TEST_PARAMETERS))
@pytest.mark.parametrize("jd", JD_LIST)
@pytest.mark.parametrize("rso", RSO_ID_COMBINATIONS)
def testEpochFetches(test_func, table, target_column, database, rso, jd, request):
    """Test truth query at a single Julian date for a unique RSO."""
    table = request.getfixturevalue(table)
    results = test_func(database, rso, jd)
    correct_rows = []
    for row in table:
        if getattr(row, target_column) in rso and row.julian_date == float(jd):
            correct_rows.append(row)
    ascending_rows = sorted(correct_rows, key=lambda d: getattr(d, target_column))
    ascending_results = sorted(results, key=lambda d: getattr(d, target_column))
    for result, correct_row in zip(ascending_results, ascending_rows):
        assert result == correct_row


TABLES = [EstimateEphemeris, TruthEphemeris, Observation]


@pytest.mark.parametrize("jd", JD_LIST)
@pytest.mark.parametrize(("sat_data", "target_column"), zip(TABLES, TARGET_COLUMN_NAMES))
def testSingleJulianDateFiltering(sat_data, target_column, jd):
    """Test filtering logic for single Julian date arguments."""
    filtered_query = filterBySingleJulianDate(Query(sat_data), sat_data, jd)
    assert isinstance(filtered_query, Query)
    epoch_query = jdEpochQuery(sat_data, target_column, [1], jd)
    assert isinstance(epoch_query, Query)


@pytest.mark.parametrize("jd_span", JD_SPANS)
@pytest.mark.parametrize(("sat_data", "target_column"), zip(TABLES, TARGET_COLUMN_NAMES))
def testJulianDateRangeFiltering(sat_data, target_column, jd_span):
    """Test filtering logic for span Julian date arguments."""
    jd_lb, jd_ub = jd_span
    if not jd_lb:
        jd_lb = 0.0
    if not jd_ub:
        jd_ub = float("inf")
    filtered_query = filterByJulianDateInterval(
        Query(sat_data),
        sat_data,
        jd_lb=JulianDate(jd_lb),
        jd_ub=JulianDate(jd_ub),
    )
    assert isinstance(filtered_query, Query)
    interval_query = jdIntervalQuery(
        sat_data,
        target_column,
        [1],
        JulianDate(jd_lb),
        JulianDate(jd_ub),
    )
    assert isinstance(interval_query, Query)


@pytest.mark.parametrize(("sat_data", "target_column"), zip(TABLES, TARGET_COLUMN_NAMES))
def testSingleBadJulianDate(sat_data, target_column):
    """Test filtering logic for bad single Julian date argument."""
    jd = 2458207.010416667
    with pytest.raises(TypeError):
        filterBySingleJulianDate(Query(sat_data), sat_data, jd)
    with pytest.raises(TypeError):
        jdEpochQuery(sat_data, target_column, [1], jd)


BAD_JD_SPAN_TYPES = [
    [2458207.010416667, JulianDate(2459304.21875)],  # lb is float
    [JulianDate(2458207.010416667), 2459304.21875],  # ub is float
    [2458207.010416667, 2459304.21875],  # both are floats
]


@pytest.mark.parametrize("jd_span", BAD_JD_SPAN_TYPES)
@pytest.mark.parametrize(("sat_data", "target_column"), zip(TABLES, TARGET_COLUMN_NAMES))
def testBadJulianDateSpanType(sat_data, target_column, jd_span):
    """Test filtering logic for bad Julian date argument."""
    with pytest.raises(TypeError):
        filterByJulianDateInterval(Query(sat_data), sat_data, jd_lb=jd_span[0], jd_ub=jd_span[1])
    with pytest.raises(TypeError):
        jdIntervalQuery(sat_data, target_column, [1], jd_span[0], jd_ub=jd_span[1])


@pytest.mark.parametrize("jd_span", BAD_JD_SPAN_BOUNDS)
@pytest.mark.parametrize(("sat_data", "target_column"), zip(TABLES, TARGET_COLUMN_NAMES))
def testBadJulianDateSpanBounds(sat_data, target_column, jd_span):
    """Test filtering logic for bad Julian date argument."""
    error_msg = "Julian date lower bound is greater than the upper bound"
    with pytest.raises(ValueError, match=error_msg):
        filterByJulianDateInterval(Query(sat_data), sat_data, jd_lb=jd_span[0], jd_ub=jd_span[1])
    with pytest.raises(ValueError, match=error_msg):
        jdIntervalQuery(sat_data, target_column, [1], jd_span[0], jd_ub=jd_span[1])
