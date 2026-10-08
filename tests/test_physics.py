"""Check forcing signs and exact inviscid balance before solver integration."""
import sys
import unittest
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ustc_les.physics import coriolis_parameter, geostrophic_acceleration, inertial_solution


class PhysicsTests(unittest.TestCase):
    def test_geostrophic_equilibrium(self):
        self.assertEqual(geostrophic_acceleration(8., 2., 8., 2., 1.e-4), (0., 0.))

    def test_rotation_sign_and_equatorial_limit(self):
        f = coriolis_parameter(31.84)
        self.assertGreater(f, 0)
        self.assertAlmostEqual(coriolis_parameter(-31.84), -f)
        self.assertEqual(coriolis_parameter(0), 0.)
        self.assertLess(geostrophic_acceleration(9., 0., 8., 0., f)[1], 0.)
        with self.assertRaises(ValueError):
            coriolis_parameter(91)

    def test_numerical_forcing_matches_exact_inertial_orbit(self):
        f = coriolis_parameter(31.84)
        times = np.linspace(0, 2 * np.pi / f, 101)
        result = solve_ivp(lambda t, uv: geostrophic_acceleration(*uv, 8., 0., f),
                           (0, times[-1]), [10., 1.], t_eval=times, rtol=1.e-10, atol=1.e-12)
        self.assertTrue(result.success)
        expected = inertial_solution(times, 10., 1., 8., 0., f)
        np.testing.assert_allclose(result.y, expected, atol=5.e-9, rtol=1.e-9)
        np.testing.assert_allclose((result.y[0] - 8)**2 + result.y[1]**2, 5., atol=5.e-9)


if __name__ == "__main__":
    unittest.main()
