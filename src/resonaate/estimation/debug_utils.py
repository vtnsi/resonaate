"""Defines supporting functions that help users debug numerical issues with filtering."""

from __future__ import annotations

# Standard Library Imports
import json
import os
import pickle
from uuid import uuid4

# Third Party Imports
import numpy as np
from mjolnir import KeyValueStore
from scipy.linalg import cholesky, inv, norm
from scipy.spatial.distance import mahalanobis
from sqlalchemy.orm import Query

# Local Imports
from ..common.behavioral_config import BehavioralConfig
from ..common.utilities import getTypeString
from ..data import getDBConnection
from ..data.ephemeris import TruthEphemeris
from ..data.query_util import addAlmostEqualFilter
from ..physics.maths import nearestPD
from ..physics.measurements import getAzimuth, getElevation, getRange, getRangeRate
from ..physics.time.stardate import julianDateToDatetime
from ..physics.transforms.methods import ecef2sez, eci2ecef


def debugToJSONFile(base_filename, debug_dir, json_dict):
    """Write debugging information to a JSON file.

    Args:
        base_filename (str): name of the file which to write to
        debug_dir (str): sub-directory of output where file will be written
        json_dict (dict): debugging data to be written to the file

    Returns:
        str: complete path and filename of the debug JSON file
    """
    # Determine and create, if necessary, the debugging directory
    out_dir = os.path.join(BehavioralConfig.getConfig().debugging.OutputDirectory, debug_dir)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    # Determine complete filepath
    complete_filename = os.path.abspath(f"{out_dir}/{base_filename}.json")

    # Write to debugging file & return complete filepath
    with open(complete_filename, "w", encoding="utf-8") as out_file:
        json.dump(json_dict, out_file)

    return complete_filename


def checkThreeSigmaObs(current_obs, sigma=3):
    """Check if an :class:`.Observation`'s absolute error is greater than 3 std."""
    target_agents = pickle.loads(KeyValueStore.getValue("target_agents"))
    sensor_agents = pickle.loads(KeyValueStore.getValue("sensor_agents"))
    shared_interface = getDBConnection()
    filenames = []
    for observation in current_obs:
        # Grab ephemeris directly from the Database to avoid any noise potentially associated
        # with `Spacecraft` objects.
        query = Query([TruthEphemeris]).filter(TruthEphemeris.agent_id == observation.target_id)
        query = addAlmostEqualFilter(query, TruthEphemeris, "julian_date", observation.julian_date)
        ephem = shared_interface.getData(query, multi=False)

        # Calculate SEZ vector from ephemeris state
        sensor_agent = sensor_agents[observation.unique_id]
        ob_ephem = eci2ecef(np.asarray(ephem.eci), julianDateToDatetime(observation.julian_date))
        ephem_minus_sensor_ecef = ob_ephem - sensor_agent.ecef_state
        ephem_sez = ecef2sez(
            ephem_minus_sensor_ecef,
            sensor_agent.lla_state[0],
            sensor_agent.lla_state[1],
        )

        # Calculate SEZ vector from observation azimuth, elevation, (and range) measurements
        # since they include measurement noise and these are the values used to update filters.
        obs_sez_from_azel_hat = np.asarray(
            [
                -np.cos(observation.elevation_rad) * np.cos(observation.azimuth_rad),
                np.cos(observation.elevation_rad) * np.sin(observation.azimuth_rad),
                np.sin(observation.elevation_rad),
            ],
        )

        if observation.dim > 2:
            obs_sez_from_azel = observation.range_km * obs_sez_from_azel_hat

        else:
            obs_sez_from_azel = norm(ephem_sez[0:3]) * obs_sez_from_azel_hat

        true_measurements = [getAzimuth(ephem_sez), getElevation(ephem_sez)]
        if observation.dim == 3:
            true_measurements.append(getRange(ephem_sez))
        elif observation.dim == 4:
            true_measurements.append(getRange(ephem_sez))
            true_measurements.append(getRangeRate(ephem_sez))

        # Difference between SEZ vector calculated from ephemeris and `xSEZ` attribute of the
        # observation. These vectors are expected to be identical, so this difference *should*
        # be zero.
        sez_diff = np.absolute(norm(ephem_sez[0:3] - observation.sez[0:3]))

        dist = mahalanobis(
            true_measurements,
            observation.measurement_states,
            inv(sensor_agent.sensors.r_matrix),
        )

        meas_diff = norm(true_measurements - np.asarray(observation.measurement_states))

        # Difference between SEZ vector calculated from ephemeris and SEZ vector calculated
        # from observation measurements. These values are expected to be different due to
        # measurement noise, but should fall within three sigma noise limit 99.7% of the time.
        sez_from_azel_diff = np.absolute(norm(ephem_sez[0:3] - obs_sez_from_azel))

        # Calculate three sigma noise limit based on sensor's R matrix.
        noise_limit = norm(sigma * sensor_agent.sensors._sqrt_noise_covar)  # noqa: SLF001

        if sez_diff > 1e-8 or dist > sigma or meas_diff > noise_limit:
            target = target_agents[observation.target_id]

            # Base debug info
            description = {
                "ephem_sez": ephem_sez.tolist(),
                "obs_sez": obs_sez_from_azel.tolist(),
                "sez_difference": sez_diff,
                "azel_difference": sez_from_azel_diff,
                "mahalanobis_distance": dist,
                "measurement_difference": meas_diff,
                "noise_limit_mag": noise_limit,
                "observation": observation.makeDictionary(),
                "sensing_agent": sensor_agent.getCurrentEphemeris().makeDictionary(),
                "target_agent": target.getCurrentEphemeris().makeDictionary(),
            }

            # Add information to debug dict
            description["sensing_agent"].update(
                {
                    "lla_state": sensor_agent.lla_state.tolist(),
                    "ecef_state": sensor_agent.ecef_state.tolist(),
                    "time": sensor_agent.time,
                },
            )
            description["truth_ephemeris"] = {
                "sat_num": ephem.unique_id,
                "julian_date": ephem.julian_date,
                "eci": ephem.eci,
            }
            description["target_agent"].update(
                {"ecef_state": target.ecef_state.tolist(), "time": target.time},
            )

            # Write to debug file, and add to filenames
            filename = f"bad_ob_{float(observation.julian_date)}_{target.simulation_id}_{sensor_agent.simulation_id}"
            complete_filename = debugToJSONFile(
                filename,
                BehavioralConfig.getConfig().debugging.ThreeSigmaObsDirectory,
                description,
            )
            filenames.append(complete_filename)

    return filenames


def findNearestPositiveDefiniteMatrix(covariance):
    """Finds the nearest PD matrix of the given covariance.

    This is primarily for numerically stabilizing covariances that become poorly conditioned. This
    function also logs the covariance for before & after the change.

    Args:
        covariance (numpy.ndarray): covariance matrix to be changed to PD

    Returns:
        ``ndarray``: cholesky factorization of the nearest PD matrix
    """
    # Factor the nearest positive definite matrix
    nearest_pd = nearestPD(covariance)
    cholesky_p = cholesky(nearest_pd)

    # Save the original covariance, nearest PD matrix, factorized matrix
    description = {
        "orig_covar": covariance.tolist(),
        "nearestPD": nearest_pd.tolist(),
        "cholesky_p": cholesky_p.tolist(),
    }

    # Write information to output file
    filename = f"not-pos-def_{str(uuid4().hex)[:8]}"
    _ = debugToJSONFile(
        filename,
        BehavioralConfig.getConfig().debugging.NearestPDDirectory,
        description,
    )

    return cholesky_p


def logFilterStep(filter_obj, observations, truth_state):
    """Log information from a complete filter step for debugging purposes.

    This occurs at the end of the :meth:`.SequentialFilter.update` logic.

    Args:
        filter_obj (:class:`.SequentialFilter`): filter object which is being logged
        observations (list): :class:`.Observation` objects associated with this filter step
        truth_state (numpy.ndarray): 6x1 ECI state vector of the estimate's truth dynamics

    Returns:
        str: filename where the filter step information was logged
    """
    # Add data to filter description
    filter_description = createFilterDebugDict(
        filter_obj,
        observations,
        truth_state,
        pickle.loads(KeyValueStore.getValue("sensor_agents")),
    )

    # Write information to output file
    filename = f"err-inflation_{float(filter_obj.time)}_{filter_obj.target_id}"
    return debugToJSONFile(
        filename,
        BehavioralConfig.getConfig().debugging.EstimateErrorInflationDirectory,
        filter_description,
    )


def createFilterDebugDict(filter_obj, observations, truth_state, sensor_agents):
    """Create the dictionary used to log filter step information.

    Args:
        filter_obj (:class:`.SequentialFilter`): filter object which is being logged
        observations (list): :class:`.Observation` objects associated with this filter step
        truth_state (numpy.ndarray): 6x1 ECI state vector of the estimate's truth dynamics
        sensor_agents (dict): collection of :class:`.SensingAgent` objects in the simulation

    Returns:
        dict: complete dictionary with relevant filter step information
    """
    # Save truth ECI state & filter constants
    description = {
        "truth_eci": truth_state.tolist(),
        "q_matrix": filter_obj.q_matrix.tolist(),
    }
    if getTypeString(filter_obj) == "UnscentedKalmanFilter":
        description.update(filter_obj.parameters)
        description["gamma"] = filter_obj.gamma

    # Update debugging information from valid observation
    for item, observation in enumerate(observations):
        sensor_agent = sensor_agents[observation.unique_id]
        description[f"observation_{item}"] = observation.makeDictionary()
        description[f"facility_{item}"] = sensor_agent.getCurrentEphemeris().makeDictionary()
        description[f"facility_{item}"].update(
            {
                "lla_state": sensor_agent.lla_state.tolist(),
                "ecef_state": sensor_agent.ecef_state.tolist(),
                "time": sensor_agent.time,
            },
        )

    # Update information from the prediction step data
    prediction_result = filter_obj.getPredictionResult()
    description["time"] = prediction_result["time"]
    description["predicted_state"] = prediction_result["pred_x"].tolist()
    description["predicted_covar"] = prediction_result["pred_p"].tolist()
    description["predicted_error"] = np.absolute(norm(truth_state - prediction_result["pred_x"]))
    description["sigma_points"] = prediction_result["sigma_points"].tolist()
    description["sigma_x_res"] = prediction_result["sigma_x_res"].tolist()

    # Update information from the forecast step data
    forecast_result = filter_obj.getForecastResult()
    description["is_angular"] = forecast_result["is_angular"].tolist()
    description["est_y"] = forecast_result["est_y"].tolist()
    description["sigma_y_res"] = forecast_result["sigma_y_res"].tolist()
    description["r_matrix"] = forecast_result["r_matrix"].tolist()
    description["cross_cvr"] = forecast_result["cross_cvr"].tolist()
    description["innov_cvr"] = forecast_result["innov_cvr"].tolist()
    description["kalman_gain"] = forecast_result["kalman_gain"].tolist()
    description["covar_after"] = forecast_result["est_p"].tolist()

    # Update information from the update step data
    update_result = filter_obj.getUpdateResult()
    description["estimate_after"] = update_result["est_x"].tolist()
    description["error_after"] = np.absolute(norm(truth_state - update_result["est_x"]))
    description["innovation"] = update_result["innovation"].tolist()
    description["nis"] = update_result["nis"].tolist()

    return description
