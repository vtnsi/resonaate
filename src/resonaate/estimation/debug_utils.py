"""Defines supporting functions that help users debug numerical issues with filtering."""

from __future__ import annotations

# Standard Library Imports
import json
import os
from typing import TYPE_CHECKING
from uuid import uuid4

# Third Party Imports
import numpy as np
from scipy.linalg import cholesky, inv, norm
from scipy.spatial.distance import mahalanobis

# Local Imports
from ..common.behavioral_config import BehavioralConfig
from ..physics.maths import nearestPD
from ..physics.measurements import getAzimuth, getElevation, getRange, getRangeRate
from ..physics.transforms.methods import ecef2sez

if TYPE_CHECKING:
    # Local Imports
    from ..agents.sensing_agent import SensingAgent
    from ..agents.target_agent import TargetAgent
    from ..data.observation import Observation


def debugToJSONFile(base_filename: str, debug_dir: str, json_dict: dict) -> str:
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


def checkThreeSigmaObservation(
    sensor_agent: SensingAgent,
    target_agent: TargetAgent,
    observation: Observation,
    sigma: int = 3,
) -> str | None:
    """Check if an :class:`.Observation`'s absolute error is greater than 3 std.

    Args:
        sensor_agent: The :class:`.SensorAgent` that collected the `observation`.
        target_agent: The :class:`.TargetAgent` that `observation` was collected on.
        observation: The :class:`.Observation` to check.
        sigma: The threshold for a detection.

    Returns:
        If this check passes, returns ``None``. If this check fails, returns a string path to the
            output file where debugging information was written.
    """
    diff = 0
    diff += observation.julian_date - sensor_agent.julian_date_epoch
    diff += observation.julian_date - target_agent.julian_date_epoch
    if diff > 2 * np.spacing(observation.julian_date):
        raise RuntimeError("Target, sensor, and observation time need to match.")

    ephem_minus_sensor_ecef = target_agent.ecef_state - sensor_agent.ecef_state
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

    output_path = None
    if sez_diff > 1e-8 or dist > sigma or meas_diff > noise_limit:
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
            "target_agent": target_agent.getCurrentEphemeris().makeDictionary(),
        }

        # Add information to debug dict
        description["sensing_agent"].update(
            {
                "lla_state": sensor_agent.lla_state.tolist(),
                "ecef_state": sensor_agent.ecef_state.tolist(),
                "time": sensor_agent.time,
            },
        )
        description["target_agent"].update(
            {
                "ecef_state": target_agent.ecef_state.tolist(),
                "time": float(target_agent.time),
            },
        )

        # Write to debug file, and add to filenames
        filename = f"bad_ob_{float(observation.julian_date)}_{target_agent.simulation_id}_{sensor_agent.simulation_id}"
        output_path = debugToJSONFile(
            filename,
            BehavioralConfig.getConfig().debugging.ThreeSigmaObsDirectory,
            description,
        )
    return output_path


def findNearestPositiveDefiniteMatrix(covariance: np.ndarray) -> np.ndarray:
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
