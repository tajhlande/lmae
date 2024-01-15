import unittest

from math import pi, degrees

from world_clock import (compute_sun_declination, compute_terminator_for_declination_and_angle, is_equinox,
                         gall_peters_projection)


class TestWorldClock(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, False)  # add assertion here

    def test_is_equinox(self):
        self.assertFalse(is_equinox(compute_sun_declination(1)))

        self.assertFalse(is_equinox(compute_sun_declination(79)))
        self.assertTrue(is_equinox(compute_sun_declination(80)))
        self.assertFalse(is_equinox(compute_sun_declination(81)))

        self.assertFalse(is_equinox(compute_sun_declination(265)))
        self.assertTrue(is_equinox(compute_sun_declination(266)))
        self.assertFalse(is_equinox(compute_sun_declination(267)))

        self.assertFalse(is_equinox(compute_sun_declination(365)))
        self.assertFalse(is_equinox(compute_sun_declination(366)))

    def test_compute_terminator(self):
        angle = 0
        step = 2 * pi / 64

        # summer solstice
        ssol_day_of_year = 172  # summer solstice
        ssol_declination = compute_sun_declination(ssol_day_of_year)
        print(f"Sun declination on summer solstice (day {ssol_day_of_year}) is {ssol_declination}")
        self.assertGreater(ssol_declination, 0)

        ssol_lat_long = compute_terminator_for_declination_and_angle(ssol_declination, 12, 0)
        print(f"Angle: {0}, lat/long: {ssol_lat_long[0]:.4f}, {ssol_lat_long[1]:.4f}")
        self.assertEqual(round(ssol_lat_long[0], 4), 0)
        self.assertEqual(round(ssol_lat_long[1], 4), 90)

        ssol_lat_long = compute_terminator_for_declination_and_angle(ssol_declination, 12, 90)
        print(f"Angle: {90}, lat/long: {ssol_lat_long[0]:.4f}, {ssol_lat_long[1]:.4f}")
        self.assertGreater(ssol_lat_long[0], 0)
        self.assertTrue(ssol_lat_long[1] < -90 or ssol_lat_long[1] > 90)

        ssol_lat_long = compute_terminator_for_declination_and_angle(ssol_declination, 12, 180)
        self.assertEqual(round(ssol_lat_long[0], 4), 0)
        self.assertEqual(round(ssol_lat_long[1], 4), -90)
        print(f"Angle: {180}, lat/long: {ssol_lat_long[0]:.4f}, {ssol_lat_long[1]:.4f}")

        ssol_lat_long = compute_terminator_for_declination_and_angle(ssol_declination, 12, 270)
        print(f"Angle: {270}, lat/long: {ssol_lat_long[0]:.4f}, {ssol_lat_long[1]:.4f}")
        self.assertLess(ssol_lat_long[0], 0)
        self.assertTrue(-90 <= ssol_lat_long[1] <= 90)

        # winter solstice
        wsol_day_of_year = 356  # winter solstice
        wsol_declination = compute_sun_declination(wsol_day_of_year)
        print(f"Sun declination on winter solstice (day {wsol_day_of_year}) is {wsol_declination}")
        self.assertLess(wsol_declination, 0)

        wsol_lat_long = compute_terminator_for_declination_and_angle(wsol_declination, 12, 0)
        print(f"Angle: {0}, lat/long: {wsol_lat_long[0]:.4f}, {wsol_lat_long[1]:.4f}")
        self.assertEqual(round(wsol_lat_long[0], 4), 0)
        self.assertEqual(round(wsol_lat_long[1], 4), 90)

        wsol_lat_long = compute_terminator_for_declination_and_angle(wsol_declination, 12, 90)
        print(f"Angle: {90}, lat/long: {wsol_lat_long[0]:.4f}, {wsol_lat_long[1]:.4f}")
        self.assertGreater(wsol_lat_long[0], 0)
        self.assertTrue(-90 <= wsol_lat_long[1] <= 90)

        wsol_lat_long = compute_terminator_for_declination_and_angle(wsol_declination, 12, 180)
        print(f"Angle: {180}, lat/long: {wsol_lat_long[0]:.4f}, {wsol_lat_long[1]:.4f}")
        self.assertEqual(round(wsol_lat_long[0], 4), 0)
        self.assertEqual(round(wsol_lat_long[1], 4), -90)

        wsol_lat_long = compute_terminator_for_declination_and_angle(wsol_declination, 12, 270)
        print(f"Angle: {270}, lat/long: {wsol_lat_long[0]:.4f}, {wsol_lat_long[1]:.4f}")
        self.assertLess(wsol_lat_long[0], 0)
        self.assertTrue(wsol_lat_long[1] < -90 or wsol_lat_long[1] > 90)

        # spring equinox
        sprex_day_of_year = 80
        sprex_declination = compute_sun_declination(sprex_day_of_year)
        print(f"Sun declination on spring equinox (day {sprex_day_of_year}) is {sprex_declination}")
        self.assertTrue(is_equinox(sprex_declination))

        sprex_lat_long = compute_terminator_for_declination_and_angle(sprex_declination, 12, 0)
        print(f"Angle: {0}, lat/long: {sprex_lat_long[0]:.4f}, {sprex_lat_long[1]:.4f}")
        self.assertEqual(round(sprex_lat_long[0], 4), 0)
        self.assertEqual(round(sprex_lat_long[1], 4), 90)

        sprex_lat_long = compute_terminator_for_declination_and_angle(sprex_declination, 12, 90)
        print(f"Angle: {90}, lat/long: {sprex_lat_long[0]:.4f}, {sprex_lat_long[1]:.4f}")
        self.assertAlmostEqual(sprex_lat_long[0], 90, 1)
        self.assertAlmostEqual(sprex_lat_long[1], 0, 1)

        sprex_lat_long = compute_terminator_for_declination_and_angle(sprex_declination, 12, 180)
        print(f"Angle: {180}, lat/long: {sprex_lat_long[0]:.4f}, {sprex_lat_long[1]:.4f}")
        self.assertEqual(round(sprex_lat_long[0], 4), 0)
        self.assertEqual(round(sprex_lat_long[1], 4), -90)

        sprex_lat_long = compute_terminator_for_declination_and_angle(sprex_declination, 12, 270)
        print(f"Angle: {270}, lat/long: {sprex_lat_long[0]:.4f}, {sprex_lat_long[1]:.4f}")
        self.assertAlmostEqual(sprex_lat_long[0], -90, 1)
        self.assertAlmostEqual(sprex_lat_long[1], -180, 1)

    def test_gall_peters_projection(self):
        self.assertEqual((32, 16), gall_peters_projection((0, 0)))
        self.assertEqual((32, 0), gall_peters_projection((90, 0)))
        self.assertEqual((32, 31), gall_peters_projection((-90, 0)))
        self.assertEqual((63, 0), gall_peters_projection((90, 180)))
        self.assertEqual((0, 0), gall_peters_projection((90, -180)))
        self.assertEqual((63, 31), gall_peters_projection((-90, 180)))
        self.assertEqual((0, 31), gall_peters_projection((-90, -180)))


if __name__ == '__main__':
    unittest.main()
