# pylint: disable=protected-access
# Standard Library Imports
# Third Party Imports
from numpy import array, diagflat, ones

try:
    # RESONAATE Imports
    from resonaate.dynamics.two_body import TwoBody
    from resonaate.estimation.adaptive.adaptive_filter import AdaptiveFilter
    from resonaate.estimation.adaptive.initialization import lambertInitializationFactory
    from resonaate.estimation.adaptive.mmae_stacking_utils import eciStack, stackingFactory
    from resonaate.estimation.maneuver_detection import StandardNis
    from resonaate.estimation.sequential.unscented_kalman_filter import UnscentedKalmanFilter
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import BaseTestCase

EST_X = array([6678.14, 0.0, 0.0, 0.0, 6.78953, 3.68641])
EST_P = diagflat([1.0, 2.0, 1.0, 1, 1, 1])
NOMINAL_FILTER = UnscentedKalmanFilter(
    10001, 0.0, EST_X, EST_P, TwoBody(), 3 * EST_P, StandardNis(0.01), None
)
TIMESTEP = 300
ORBIT_DETERMINATION = lambertInitializationFactory("lambert_universal")
STACKING_METHOD = stackingFactory("eci_stack")
Y_DIM = 4
HYPOTHESIS_STATES = array(
    [
        [
            1.04213762e03,
            1.03337376e03,
            6.70563235e03,
            7.45441558e00,
            9.16569904e-01,
            -1.29593066e00,
        ],
        [
            1.04213762e03,
            1.03337376e03,
            6.70563235e03,
            7.45441558e00,
            9.16569904e-01,
            -1.29593066e00,
        ],
        [
            4.96882662e03,
            1.32276258e03,
            4.55146966e03,
            5.14772605e00,
            1.23195891e-02,
            -5.61649491e00,
        ],
    ]
)


class TestStackingMethods(BaseTestCase):
    """Test Class for Stacking methods."""

    adaptive_filter = AdaptiveFilter(
        NOMINAL_FILTER, TIMESTEP, ORBIT_DETERMINATION, STACKING_METHOD, 1, 300, 1e-10, 0.997
    )
    adaptive_filter.x_dim = 6
    adaptive_filter.pred_x = EST_X
    adaptive_filter.pred_p = diagflat(ones(adaptive_filter.x_dim))
    adaptive_filter.time = 0
    adaptive_filter.is_angular = True
    adaptive_filter.source = "Observation"
    adaptive_filter.est_x = EST_X
    adaptive_filter.est_p = diagflat(ones(adaptive_filter.x_dim))
    adaptive_filter.true_y = array([0, 1])
    adaptive_filter.mean_pred_y = array([0, 1])
    adaptive_filter.cross_cvr = ones((adaptive_filter.x_dim, Y_DIM))
    adaptive_filter.innov_cvr = ones((Y_DIM, Y_DIM))
    adaptive_filter.kalman_gain = ones((adaptive_filter.x_dim, Y_DIM))
    adaptive_filter.model_weights = array([1, 1, 1])

    def testECIStacking(self):
        """Tests stacking ECI states."""
        self.adaptive_filter.stacking_method = stackingFactory("eci_stack")
        self.adaptive_filter.models = self.adaptive_filter._createModels(HYPOTHESIS_STATES)
        for model in self.adaptive_filter.models:
            model.pred_x = EST_X
        pred_x, est_x = eciStack(self.adaptive_filter.models, self.adaptive_filter.model_weights)
        assert pred_x.shape == (6,)
        assert est_x.shape == (6,)
