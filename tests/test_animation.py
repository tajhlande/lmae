import unittest

from context import lmae
from lmae.animation import Easing


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

if __name__ == '__main__':
    unittest.main()
