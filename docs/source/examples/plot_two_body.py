"""
Two Body Simulation
===================

Show propagation of Two Body dynamics.

This example demonstrates how the :class:`.TwoBody` class works along with a simple plot.
"""

# %%
# Imports
# -------

# Third Party Imports
import numpy as np
from matplotlib import pyplot as plt

# %%
# Create Initial Data
# -------------------
#
# Create the initial state, initial epoch, final epoch, and time step.
# This example uses an initial state in an orbit similar to the ISS.
# Also, the simulation propagates for one hour at one minute time steps.

# [km, km, km, km/s, km/s, km/s]
init_state = np.array(
    [-2872.57438, 3128.21583, -5311.55207, -5.250942201, -5.547484592, -0.428942173],
)
init_epoch = 0.0  # seconds
final_epoch = 3600.0  # seconds
time_step = 60.0  # seconds

# %%
# Instantiate `TwoBody`
# ---------------------
#
# Create the TwoBody object using an empty initialization function.

# RESONAATE Imports
from resonaate.dynamics.two_body import TwoBody

dynamics = TwoBody()

# %%
# Propagate Once
# --------------
#
# Propagate the dynamics over one large, hour-long time step.
# The internal integrator will control the integration time tep.

final_state = dynamics.propagate(init_epoch, final_epoch, init_state)
print(final_state)

# %%
# Propagate Multiple Times
# ------------------------
#
# To get stepped output, users can easily loop the propagation.
# This will propagate one hour at one minute steps.

states = [init_state]
times = [init_epoch]
for next_epoch in np.arange(time_step, final_epoch + time_step, time_step):
    # Propgate dynamics one step
    next_state = dynamics.propagate(init_epoch, next_epoch, init_state)
    # Append values to lists
    states.append(next_state)
    times.append(next_epoch)
    # Reset initial values
    init_epoch = next_epoch
    init_state = np.copy(next_state)

same_final_state = np.allclose(final_state, states[-1])
print(f"The bulk propagate and step propagate states are numerically close: {same_final_state}")
states = np.array(states)

# %%
# Plot Data
# --------------------
#
# Plot propagated orbit.

plt.figure()
ax1 = plt.axes(projection="3d")
ax1.scatter(states[::, 0], states[::, 1], states[::, 2], "green")
ax1.set_xlabel("x axis")
ax1.set_ylabel("y axis")
ax1.set_zlabel("z axis")
plt.show()
