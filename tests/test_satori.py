"""Unit tests for the Satori app's brightness dimming schedule."""

import os
import time
import unittest
from unittest.mock import patch

from examples.satori import SatoriApp


def _mock_localtime(hour: int, minute: int = 0, second: int = 0) -> time.struct_time:
    """Create a time.struct_time for the given wall-clock time.

    Only tm_hour/tm_min/tm_sec matter to _compute_brightness; the date
    fields are filler.
    """
    return time.struct_time((2025, 1, 1, hour, minute, second, 0, 1, 0))


class BrightnessScheduleTest(unittest.TestCase):
    """Validate the wall-clock brightness schedule at and around all transition points.

    Schedule (default daytime=100, nighttime=60)::

        05:00-06:00  gradual brightening (night -> day)
        06:00-21:00  full daytime brightness
        21:00-22:00  gradual dimming (day -> night)
        22:00-05:00  full nighttime brightness
    """

    def setUp(self):
        resource_path = os.path.join(os.path.dirname(__file__), "..", "examples")
        self.app = SatoriApp(resource_path=resource_path)

    def _brightness_at(self, hour: int, minute: int = 0) -> int:
        """Compute brightness at a specific wall-clock time."""
        mock = _mock_localtime(hour, minute)
        with patch.object(time, "localtime", return_value=mock):
            return self.app._compute_brightness()

    # --- Nighttime (before dawn) ---

    def test_midnight(self):
        """Midnight: full nighttime brightness."""
        self.assertEqual(self._brightness_at(0), 60)

    def test_4am_one_hour_before_morning_transition(self):
        """4 AM — one hour before morning transition: nighttime level."""
        self.assertEqual(self._brightness_at(4), 60)

    # --- Morning transition (05:00-06:00) ---

    def test_5am_morning_transition_start(self):
        """5:00 AM — start of morning transition: still at nighttime level."""
        self.assertEqual(self._brightness_at(5), 60)

    def test_5_30am_morning_transition_middle(self):
        """5:30 AM — middle of morning transition: between low and high."""
        b = self._brightness_at(5, 30)
        self.assertGreater(b, 60)
        self.assertLess(b, 100)
        self.assertEqual(b, 80)  # exact midpoint: round(60 + 40*0.5)

    def test_6am_morning_transition_end(self):
        """6:00 AM — end of morning transition: full daytime brightness."""
        self.assertEqual(self._brightness_at(6), 100)

    # --- Daytime ---

    def test_noon(self):
        """Noon: full daytime brightness."""
        self.assertEqual(self._brightness_at(12), 100)

    def test_8pm_one_hour_before_evening_transition(self):
        """8 PM — one hour before evening transition: daytime level."""
        self.assertEqual(self._brightness_at(20), 100)

    # --- Evening transition (21:00-22:00) ---

    def test_9pm_evening_transition_start(self):
        """9:00 PM — start of evening transition: still at daytime level."""
        self.assertEqual(self._brightness_at(21), 100)

    def test_9_30pm_evening_transition_middle(self):
        """9:30 PM — middle of evening transition: between high and low."""
        b = self._brightness_at(21, 30)
        self.assertGreater(b, 60)
        self.assertLess(b, 100)
        self.assertEqual(b, 80)  # exact midpoint: round(100 + (-40)*0.5)

    def test_10pm_evening_transition_end(self):
        """10:00 PM — end of evening transition: full nighttime brightness."""
        self.assertEqual(self._brightness_at(22), 60)

    # --- Nighttime (after dusk) ---

    def test_11pm(self):
        """11 PM: full nighttime brightness."""
        self.assertEqual(self._brightness_at(23), 60)

    # --- Just around the boundaries ---

    def test_4_59am_just_before_morning_transition(self):
        """4:59 AM — just before morning transition: nighttime."""
        self.assertEqual(self._brightness_at(4, 59), 60)

    def test_6_01am_just_after_morning_transition(self):
        """6:01 AM — just after morning transition: daytime."""
        self.assertEqual(self._brightness_at(6, 1), 100)

    def test_8_59pm_just_before_evening_transition(self):
        """8:59 PM — just before evening transition: daytime."""
        self.assertEqual(self._brightness_at(20, 59), 100)

    def test_10_01pm_just_after_evening_transition(self):
        """10:01 PM — just after evening transition: nighttime."""
        self.assertEqual(self._brightness_at(22, 1), 60)

    # --- Gradual transition is monotonic ---

    def test_morning_transition_is_monotonically_increasing(self):
        """Brightness increases (or stays equal) through the morning transition."""
        values = [self._brightness_at(5, m) for m in range(0, 60)]
        for i in range(1, len(values)):
            self.assertGreaterEqual(
                values[i],
                values[i - 1],
                f"Brightness decreased at minute {i}: {values}",
            )

    def test_evening_transition_is_monotonically_decreasing(self):
        """Brightness decreases (or stays equal) through the evening transition."""
        values = [self._brightness_at(21, m) for m in range(0, 60)]
        for i in range(1, len(values)):
            self.assertLessEqual(
                values[i],
                values[i - 1],
                f"Brightness increased at minute {i}: {values}",
            )


class BrightnessOverrideTest(unittest.TestCase):
    """Test fixed brightness override and custom day/night levels."""

    def setUp(self):
        self.resource_path = os.path.join(os.path.dirname(__file__), "..", "examples")

    def _brightness_at(self, app: SatoriApp, hour: int, minute: int = 0) -> int:
        mock = _mock_localtime(hour, minute)
        with patch.object(time, "localtime", return_value=mock):
            return app._compute_brightness()

    def test_fixed_brightness_override_at_all_times(self):
        """Fixed brightness is returned at every time of day."""
        app = SatoriApp(brightness=42, resource_path=self.resource_path)
        for hour in range(24):
            self.assertEqual(
                self._brightness_at(app, hour),
                42,
                f"Fixed brightness failed at {hour}:00",
            )

    def test_custom_day_night_levels(self):
        """Custom day/night brightness levels are respected at each phase."""
        app = SatoriApp(
            daytime_brightness=90,
            nighttime_brightness=30,
            resource_path=self.resource_path,
        )
        self.assertEqual(self._brightness_at(app, 12), 90)  # midday
        self.assertEqual(self._brightness_at(app, 0), 30)  # midnight
        # Midpoint of morning transition: round(30 + (90-30)*0.5) = 60
        self.assertEqual(self._brightness_at(app, 5, 30), 60)
        # Midpoint of evening transition: round(90 + (30-90)*0.5) = 60
        self.assertEqual(self._brightness_at(app, 21, 30), 60)

    def test_fixed_override_ignores_custom_levels(self):
        """When a fixed brightness is set, day/night levels are ignored."""
        app = SatoriApp(
            daytime_brightness=90,
            nighttime_brightness=30,
            brightness=75,
            resource_path=self.resource_path,
        )
        self.assertEqual(self._brightness_at(app, 12), 75)
        self.assertEqual(self._brightness_at(app, 0), 75)

    def test_brightness_clamping(self):
        """Out-of-range brightness values are clamped to 1-100."""
        app = SatoriApp(
            daytime_brightness=200,
            nighttime_brightness=-10,
            resource_path=self.resource_path,
        )
        self.assertEqual(app._daytime_brightness, 100)
        self.assertEqual(app._nighttime_brightness, 1)
        self.assertEqual(self._brightness_at(app, 12), 100)
        self.assertEqual(self._brightness_at(app, 0), 1)


if __name__ == "__main__":
    unittest.main()
