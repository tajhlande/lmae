import unittest
from unittest.mock import MagicMock

from lmae.animation import Easing, HueFade, Parallel, Sequence, Still


class EasingTest(unittest.TestCase):
    def test_linear_easing_invocation(self):
        easing = Easing.LINEAR
        self.assertEqual(0.0, easing.apply(0.0))
        self.assertEqual(0.25, easing.apply(0.25))
        self.assertEqual(0.5, easing.apply(0.5))
        self.assertEqual(0.75, easing.apply(0.75))
        self.assertEqual(1.0, easing.apply(1.0))

    def test_quadratic_easing_invocation(self):
        easing = Easing.QUADRATIC
        self.assertEqual(0.0, easing.apply(0.0))
        self.assertEqual(0.125, easing.apply(0.25))
        self.assertEqual(0.5, easing.apply(0.5))
        self.assertEqual(0.875, easing.apply(0.75))
        self.assertEqual(1.0, easing.apply(1.0))

    def test_bezier_easing_invocation(self):
        easing = Easing.BEZIER
        self.assertEqual(0.0, easing.apply(0.0))
        self.assertEqual(0.15625, easing.apply(0.25))
        self.assertEqual(0.5, easing.apply(0.5))
        self.assertEqual(0.84375, easing.apply(0.75))
        self.assertEqual(1.0, easing.apply(1.0))

    def test_parametric_easing_invocation(self):
        easing = Easing.PARAMETRIC
        self.assertEqual(0.0, easing.apply(0.0))
        self.assertEqual(0.1, easing.apply(0.25))
        self.assertEqual(0.5, easing.apply(0.5))
        self.assertEqual(0.9, easing.apply(0.75))
        self.assertEqual(1.0, easing.apply(1.0))

    def test_back_easing_invocation(self):
        easing = Easing.BACK
        self.assertEqual(0.0, easing.apply(0.0))
        self.assertEqual(-0.09968184375, easing.apply(0.25))
        self.assertEqual(0.5, easing.apply(0.5))
        self.assertEqual(1.09968184375, easing.apply(0.75))
        self.assertEqual(1.0, easing.apply(1.0))


class ParallelTest(unittest.TestCase):
    """Tests for the Parallel concurrent animation container."""

    def test_duration_is_max_of_children(self):
        """Parallel duration is the longest child, not the sum."""
        actor = MagicMock()
        fast = Still(actor=actor, duration=1.0)
        slow = Still(actor=actor, duration=3.0)
        parallel = Parallel(actor=actor, animations=[fast, slow])
        self.assertEqual(3.0, parallel.duration)

    def test_empty_parallel_duration_is_zero(self):
        actor = MagicMock()
        parallel = Parallel(actor=actor)
        self.assertEqual(0.0, parallel.duration)

    def test_all_children_start_simultaneously(self):
        """start() should start every child with the same timestamp."""
        actor = MagicMock()
        anim_a = Still(actor=actor, duration=2.0)
        anim_b = Still(actor=actor, duration=3.0)
        parallel = Parallel(actor=actor, animations=[anim_a, anim_b])

        parallel.start(100.0)
        self.assertTrue(anim_a.is_started())
        self.assertTrue(anim_b.is_started())
        self.assertEqual(100.0, anim_a.start_time)
        self.assertEqual(100.0, anim_b.start_time)

    def test_not_finished_until_all_children_done(self):
        """is_finished should be False while any child is still running."""
        actor = MagicMock()
        fast = Still(actor=actor, duration=1.0)
        slow = Still(actor=actor, duration=3.0)
        parallel = Parallel(actor=actor, animations=[fast, slow])

        parallel.start(100.0)

        # After 1.5s: fast is done, slow is not
        parallel.update_actor(101.5)
        self.assertTrue(fast.is_finished())
        self.assertFalse(slow.is_finished())
        self.assertFalse(parallel.is_finished())

        # After 3.5s: both done
        parallel.update_actor(103.5)
        self.assertTrue(slow.is_finished())
        self.assertTrue(parallel.is_finished())

    def test_reset_resets_all_children(self):
        actor = MagicMock()
        anim_a = Still(actor=actor, duration=1.0)
        anim_b = Still(actor=actor, duration=2.0)
        parallel = Parallel(actor=actor, animations=[anim_a, anim_b])

        parallel.start(100.0)
        parallel.update_actor(105.0)
        self.assertTrue(anim_a.is_started())
        self.assertTrue(anim_b.is_started())

        parallel.reset()
        self.assertFalse(anim_a.is_started())
        self.assertFalse(anim_b.is_started())

    def test_update_skips_finished_children(self):
        """update_actor should not call update_actor on finished children."""
        actor = MagicMock()
        fast = Still(actor=actor, duration=1.0)
        slow = Still(actor=actor, duration=3.0)
        parallel = Parallel(actor=actor, animations=[fast, slow])

        parallel.start(100.0)
        parallel.update_actor(101.5)
        self.assertTrue(fast.is_finished())

        # Fast is finished; calling update again should not error or change its state
        fast_last_update = fast.last_update_time
        parallel.update_actor(102.0)
        self.assertEqual(fast_last_update, fast.last_update_time)

    def test_add_animation_updates_duration(self):
        actor = MagicMock()
        parallel = Parallel(actor=actor, animations=[Still(actor=actor, duration=2.0)])
        self.assertEqual(2.0, parallel.duration)

        parallel.add_animation(Still(actor=actor, duration=5.0))
        self.assertEqual(5.0, parallel.duration)

    def test_nested_in_sequence(self):
        """Parallel works as an element inside a Sequence."""
        actor = MagicMock()
        show = MagicMock()
        show.is_finished.return_value = False
        show.duration = 0.001
        hide = MagicMock()
        hide.is_finished.return_value = False
        hide.duration = 0.001

        fast = Still(actor=actor, duration=1.0)
        slow = Still(actor=actor, duration=2.0)
        parallel = Parallel(actor=actor, animations=[fast, slow])

        # Sequence: show -> parallel(1s+2s) -> hide
        sequence = Sequence(
            actor=actor,
            animations=[
                show,
                parallel,
                hide,
            ],
        )

        # Duration = 0.001 + 2.0 + 0.001
        self.assertAlmostEqual(2.002, sequence.duration, places=3)

        # Start and advance past show
        sequence.start(100.0)
        show.is_finished.return_value = True
        sequence.update_actor(100.001)

        # Now parallel should be the current animation
        self.assertTrue(parallel.is_started())
        self.assertFalse(parallel.is_finished())

        # Advance past the fast child but not the slow one
        sequence.update_actor(101.5)
        self.assertFalse(parallel.is_finished())

        # Advance past both
        sequence.update_actor(103.0)
        self.assertTrue(parallel.is_finished())

        # Sequence should move to hide
        sequence.update_actor(103.001)
        self.assertTrue(hide.is_started())


class HueFadeTest(unittest.TestCase):
    """Tests for HueFade color and alpha interpolation."""

    def test_initial_color_at_start(self):
        """At fraction=0 (animation start), the callback receives initial_color."""
        received = []
        actor = MagicMock()
        fade = HueFade(
            actor=actor,
            callback=lambda c: received.append(c),
            initial_color=(255, 0, 0),
            final_color=(0, 0, 255),
            duration=2.0,
        )
        fade.start(100.0)
        fade.update_actor(100.0)  # elapsed=0, fraction=0
        self.assertEqual((255, 0, 0), received[-1])

    def test_final_color_at_end(self):
        """At fraction=1 (animation end), the callback receives final_color."""
        received = []
        actor = MagicMock()
        fade = HueFade(
            actor=actor,
            callback=lambda c: received.append(c),
            initial_color=(255, 0, 0),
            final_color=(0, 0, 255),
            duration=2.0,
        )
        fade.start(100.0)
        fade.update_actor(102.0)  # elapsed=2.0, fraction=1.0
        self.assertEqual((0, 0, 255), received[-1])

    def test_midpoint_interpolation(self):
        """At the midpoint, color should be roughly the blend of initial and final."""
        received = []
        actor = MagicMock()
        fade = HueFade(
            actor=actor,
            callback=lambda c: received.append(c),
            initial_color=(0, 0, 0),
            final_color=(255, 255, 255),
            duration=2.0,
        )
        fade.start(100.0)
        fade.update_actor(101.0)  # elapsed=1.0, fraction=0.5
        # Should be gray, roughly (127, 127, 127) or (128, 128, 128)
        r, g, b = received[-1]
        self.assertAlmostEqual(r, g, delta=2)
        self.assertAlmostEqual(g, b, delta=2)
        self.assertGreater(r, 100)
        self.assertLess(r, 156)

    def test_alpha_interpolation_rgba(self):
        """When either color has 4 components, callback receives RGBA tuples."""
        received = []
        actor = MagicMock()
        fade = HueFade(
            actor=actor,
            callback=lambda c: received.append(c),
            initial_color=(224, 224, 224, 0),
            final_color=(224, 224, 224, 255),
            duration=2.0,
        )
        fade.start(100.0)

        # Start: alpha should be 0
        fade.update_actor(100.0)
        self.assertEqual(4, len(received[-1]))
        self.assertEqual(0, received[-1][3])

        # End: alpha should be 255
        fade.update_actor(102.0)
        self.assertEqual(255, received[-1][3])

    def test_rgb_only_when_no_alpha(self):
        """When both colors are 3-tuple, callback receives 3-tuple (backward compat)."""
        received = []
        actor = MagicMock()
        fade = HueFade(
            actor=actor,
            callback=lambda c: received.append(c),
            initial_color=(255, 0, 0),
            final_color=(0, 0, 255),
            duration=1.0,
        )
        fade.start(100.0)
        fade.update_actor(100.5)
        self.assertEqual(3, len(received[-1]))

    def test_alpha_midpoint(self):
        """Alpha at midpoint should be roughly half between initial and final."""
        received = []
        actor = MagicMock()
        fade = HueFade(
            actor=actor,
            callback=lambda c: received.append(c),
            initial_color=(0, 0, 0, 0),
            final_color=(0, 0, 0, 220),
            duration=2.0,
        )
        fade.start(100.0)
        fade.update_actor(101.0)  # fraction=0.5
        alpha = received[-1][3]
        self.assertAlmostEqual(alpha, 110, delta=5)

    def test_fade_in_direction(self):
        """Fade-in: start invisible (alpha=0), end visible (alpha=255)."""
        received = []
        actor = MagicMock()
        fade = HueFade(
            actor=actor,
            callback=lambda c: received.append(c),
            initial_color=(224, 224, 224, 0),
            final_color=(224, 224, 224, 255),
            duration=1.0,
        )
        fade.start(100.0)
        fade.update_actor(100.0)
        self.assertEqual(0, received[-1][3], "Should start invisible")
        fade.update_actor(101.0)
        self.assertEqual(255, received[-1][3], "Should end visible")

    def test_fade_out_direction(self):
        """Fade-out: start visible (alpha=255), end invisible (alpha=0)."""
        received = []
        actor = MagicMock()
        fade = HueFade(
            actor=actor,
            callback=lambda c: received.append(c),
            initial_color=(224, 224, 224, 255),
            final_color=(224, 224, 224, 0),
            duration=1.0,
        )
        fade.start(100.0)
        fade.update_actor(100.0)
        self.assertEqual(255, received[-1][3], "Should start visible")
        fade.update_actor(101.0)
        self.assertEqual(0, received[-1][3], "Should end invisible")


if __name__ == "__main__":
    unittest.main()
