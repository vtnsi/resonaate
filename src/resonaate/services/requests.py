"""Functions that provide structured data for "get" requests to the Resonaate service layer."""
# Standard Library Imports
# Third Party Imports
from numpy import abs as np_abs, asarray, diagonal, sqrt, min as np_min
from scipy.linalg import norm
# RESONAATE Imports


def getAxisObject(label, unit=None, axis_min=None, axis_max=None):
    """Create a generic axis object based on required specification.

    Args:
        label (str): Displayed along axis
        unit (str, optional): Displayed in ()s with label, if present. Defaults to None.
        axis_min (str, optional): Minimum axis value. Defaults to None.
        axis_max (str, optional): Maximum axis value. Defaults to None.

    Returns:
        dict: formatted axis object
    """
    # Enforce strict typing
    if not isinstance(label, str):
        raise TypeError("Axis label must be a string.")

    # Build simple axis object
    msg = {
        "label": label
    }

    # Add units and plot min/max if desired
    if unit:
        if not isinstance(unit, str):
            raise TypeError("Axis unitLabel must be a string.")
        msg["unitLabel"] = unit
    if axis_min:
        if not isinstance(axis_min, str):
            raise TypeError("Axis min must be a string.")
        msg["min"] = axis_min
    if axis_max:
        if not isinstance(axis_max, str):
            raise TypeError("Axis max must be a string.")
        msg["max"] = axis_max

    return msg


def getSequenceData(x_values, y_values, radius=None):
    """Create a generic `Sequence` data object based on required specification.

    Args:
        x_values (str): x_values as strings
        y_values (str): y_values as strings
        tooltip (str, optional): What information the data is
        radius (float, optional): Radius of points on lines; defaults to 0

    Returns:
        dict: formatted `Sequence` data object
    """
    if radius:
        data = [{"x": str(xx), "y": str(yy), "radius": radius} for xx, yy in zip(x_values, y_values)]
    else:
        data = [{"x": str(xx), "y": str(yy)} for xx, yy in zip(x_values, y_values)]
    return data


def getSequence(label, data, line_type=None, dasharray=None, color=None, fill=None, url=None, tooltip=None):
    """Create a generic `Sequence` object based on required specification.

    Args:
        label (str): Displayed to user as line label
        data (data): x and y values of the data object
        line_type (str, optional): type of line chart. e.g. "curveLinear", "curveMonotoneX", "curveStep"
        dasharray (str, optional): Values for creating dashed lines
        color (str, optional): RGB hex string for the line color (e.g., “#FF0000”)
        fill (str, optional): RGB hex string for the color to fill under the line (e.g., “#FF0000”)
        url (URL, optional): URL where more information about a sequence may be provided
        tooltip (str, optional): What information the sequence is

    Returns:
        dict: formatted `Sequence` object
    """
    # Build simple sequence object
    msg = {
        "label": label,
        "data": data,
    }

    # Add args for sequence if desired
    if line_type:
        msg["type"] = line_type
    if dasharray:
        msg["dasharray"] = dasharray
    if color:
        msg["color"] = color
    if fill:
        msg["fill"] = fill
    if url:
        msg["url"] = url
    if tooltip:
        msg["tooltip"] = tooltip

    return msg


def getBarChart(timestamps, observations):
    """Get single stacked `BarChart` data object.

    Args:
        timestamps (list): Nx1 list of timestamps
        observations (list): list of formatted observation dictionaries

    Returns:
        list: dictionaries describing each `BarChart` object to add
    """
    ## [TODO]: Add visibility check into the logic
    # Create dict with sensors' names as the keys, and the values are
    #   list where successful observations of the target ocurred
    sensors = dict()
    for observation in observations:
        sensor = observation["observer"]
        timestamp = observation["timestampISO"]
        # Add all timestamps for each sensor
        try:
            sensors[sensor].append(timestamp)
        except KeyError:
            sensors[sensor] = [timestamp]

    # Build empty bar objects
    bar_chart = [dict(label=sensor, data=[]) for sensor in sensors]

    # Create bar chart entry for each timestamp
    for timestamp in timestamps:
        for empty_bar in bar_chart:
            # Default data produces an error
            data = {
                "value": timestamp,
                "label": "none"
            }
            # Check if the timestamp associated with an observation
            obs_times = sensors[empty_bar["label"]]
            if timestamp in obs_times:
                data["label"] = "low"
                data["tooltip"] = "Successful Observation"
            ## [TODO]: Add a continue to the observed, then add visibility logic
            empty_bar["data"].append(data)

    return bar_chart


def getObservationBarChart(sat_num, timestamps, estimates, observations):
    """Build a visibility and observation request message.

    Args:
        sat_num (int): SATCAT number of the satellite
        timestamps (list): Nx1 list of timestamps
        estimates (``numpy.ndarray``): 6XN array of estimate ephemerides
        observations (list): list of formatted observation dictionaries

    Returns:
        dict: valid single stacked bar chart message
    """
    assert estimates.shape == (6, len(timestamps)), "VisibilityRequest: Incorrect state dimension of estimates"
    request = {
        "label": f"Observations for {sat_num}",      # chart header/title
        "xAxis": getAxisObject("Time", unit="UTC"),  # x axis attributes
        "barGroups": [                               # `BarGroup` objects to plot
            {
                "bars": getBarChart(timestamps, observations)
            }
        ]
    }
    return request


def getRSODistanceLineChart(primary_sat_num, primary_est_hist, secondary_est_hist):
    """Distance between RSO line chart.

    Args:
        primary_sat_num (int): SATCAT number of primary target
        primary_est_hist (list): 6xN array of primary target estimate ephemerides
        secondary_sat_num (int): SATCAT number of secondary target
        secondary_est_hist (list): 6xN array of secondary target estimate ephemerides

    Returns:
        dict: formatted line chart object for distance between two RSOs
    """
    # Build primary estimate timestamp set
    pri_timestamps = {est['timestampISO'] for est in primary_est_hist}
    data = {}
    min_distances = []
    for rso_id, sec_est in secondary_est_hist.items():
        # Build secondary timestamp set, and find intersection with the primary set
        sec_timestamps = {est['timestampISO'] for est in sec_est}
        timestamps = sorted(list(pri_timestamps.intersection(sec_timestamps)))

        # Get the subset of each RSOs state vectors that correspond to the timestamp intersection
        sec_estimates = getSortedEstimates(timestamps, sec_est)
        pri_estimates = getSortedEstimates(timestamps, primary_est_hist)

        # Calculate the RSO distance & find the minimum distance
        distance = pri_estimates - sec_estimates
        distance = norm(distance[0:3, :], axis=0)
        min_distances.append(np_min(distance))

        # Final check for valid data, and then create the plot data.
        assert len(timestamps) == distance.shape[0]
        data[rso_id] = getSequenceData(timestamps, distance, radius=1)

    title = f"Distance to RSO {primary_sat_num}"
    msg = {
        "label": title,                                             # Header/title
        "xAxis": getAxisObject("Time", unit="UTC"),                 # x axis attributes
        "yAxis": getAxisObject("Total Distance", unit="km"),        # y axis attributes
        "sequences": [getSequence(rso_id, rso_data) for rso_id, rso_data in data.items()]
    }

    return msg, np_min(min_distances)


def getSortedEstimates(timestamps, estimates):
    """Build a subset of state vectors based on the given timestamps.

    Args:
        timestamps (set): timestamps set of the intersection of primary & secondary timestamps
        estimates (list): estimate messages to build from

    Returns:
        ``numpy.ndarray``: subset of state vectors
    """
    est = [est['position'] + est['velocity'] for est in estimates if est["timestampISO"] in timestamps]

    return asarray(est).transpose()


def getCovarianceLineChart(sat_num, timestamps, covar_hist, sigmas, labels):
    """Covariance line chart object with multiple lines.

    Args:
        sat_num (int): SATCAT number of target
        time_stamps (list): Nx1 list of ISO timestamps
        covar_hist (list): list of 6x6 covariance histories for each timestamp
        sigmas (tuple): sigma values used to calculate percentage lines
        labels (tuple): labels associated with each percentage line

    Returns:
        dict: formatted line chart objects for uncertainty percentages
    """
    # Enforce strict typing
    if not isinstance(sigmas, tuple):
        raise TypeError('Sigma values must be entered as a tuple')
    if not isinstance(labels, tuple):
        raise TypeError('Label values must be entered as a tuple')
    if len(sigmas) != len(labels):
        raise ValueError('Must include a label for each sigma value')

    # Calculate the positional uncertainty for each percentage
    sigma_sets = [[] for _ in sigmas]
    for covar in covar_hist:
        sigma_pos_values = sqrt(np_abs(diagonal(asarray(covar))[:3]))
        for sigma_set, sigma in zip(sigma_sets, sigmas):
            sigma_set.append(norm(sigma * sigma_pos_values))

    # Format the data properly
    dataset = [getSequenceData(timestamps, sigma) for sigma in sigma_sets]

    # Build the complete reply message
    msg = {
        "label": f"Covariance Magnitude for {sat_num}",                                  # Header/title
        "xAxis": getAxisObject("Time", unit="UTC"),                                      # x axis attributes
        "yAxis": getAxisObject("Estimated Uncertainty", unit="km"),                      # y axis attributes
        "sequences": [getSequence(label, data) for label, data in zip(labels, dataset)]  # `Sequence` objects to plot
    }

    return msg
