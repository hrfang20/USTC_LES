"""Coordinates: x east, y north, z up. SI units throughout."""
import math
import numpy as np

EARTH_ROTATION_S_INV = 7.292115e-5


def coriolis_parameter(latitude_deg):
    """Traditional vertical Coriolis parameter f = 2 Omega sin(latitude)."""
    if not math.isfinite(latitude_deg) or not -90 <= latitude_deg <= 90:
        raise ValueError("Latitude must be finite and in [-90, 90] degrees")
    return 2 * EARTH_ROTATION_S_INV * math.sin(math.radians(latitude_deg))


def geostrophic_acceleration(u, v, ug, vg, f):
    """Combined Coriolis and background pressure-gradient acceleration.

    du/dt = f(v - Vg), dv/dt = -f(u - Ug).
    This is only the forcing term, not a turbulence or wall model.
    """
    return f * (np.asarray(v) - vg), -f * (np.asarray(u) - ug)


def inertial_solution(time_s, u0, v0, ug, vg, f):
    """Exact homogeneous inviscid solution; no buildings or boundary layer."""
    phase = f * np.asarray(time_s)
    a, b = u0 - ug, v0 - vg
    return (ug + a * np.cos(phase) + b * np.sin(phase),
            vg - a * np.sin(phase) + b * np.cos(phase))
