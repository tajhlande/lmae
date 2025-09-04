import os.path
from unittest import TestCase
import logging
import freezegun
from PIL import Image

from lmae.core import Stage
from examples.advent_app import AdventApp

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)12s [%(levelname)5s]: %(message)s')


class MatrixMock:
    pass


# noinspection DuplicatedCode
class TestAdventApp(TestCase):

    def test_countdown_text(self):
        # logger = logging.getLogger("TestAdventApp.test_countdown_text")
        resource_path = os.path.join(os.path.dirname(__file__), "../examples")
        advent_app = AdventApp(font_path=os.path.join(resource_path, "fonts"),
                               image_path=os.path.join(resource_path, "images"))
        matrix = MatrixMock()
        matrix.CreateFrameCanvas = lambda : Image.new("L", size=(10, 10), color=0)
        advent_app.stage = Stage()
        with freezegun.freeze_time("2023-12-01 12:00:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertTrue(advent_app.counter_label.visible)
            self.assertEqual(advent_app.counter_label.text, "24")
            self.assertFalse(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "days")
            self.assertEqual(advent_app.line_2_label.text, "until")

        with freezegun.freeze_time("2023-12-23 12:00:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertTrue(advent_app.counter_label.visible)
            self.assertEqual(advent_app.counter_label.text, "2")
            self.assertFalse(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "days")
            self.assertEqual(advent_app.line_2_label.text, "until")

        with freezegun.freeze_time("2023-12-23 23:59:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertTrue(advent_app.counter_label.visible)
            self.assertEqual(advent_app.counter_label.text, "2")
            self.assertFalse(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "days")
            self.assertEqual(advent_app.line_2_label.text, "until")

        with freezegun.freeze_time("2023-12-24 00:00:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertTrue(advent_app.counter_label.visible)
            self.assertEqual(advent_app.counter_label.text, "24")
            self.assertFalse(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "hours")
            self.assertEqual(advent_app.line_2_label.text, "until")

        with freezegun.freeze_time("2023-12-24 00:01:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertTrue(advent_app.counter_label.visible)
            self.assertEqual(advent_app.counter_label.text, "24")
            self.assertFalse(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "hours")
            self.assertEqual(advent_app.line_2_label.text, "until")

        with freezegun.freeze_time("2023-12-24 12:00:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertTrue(advent_app.counter_label.visible)
            self.assertEqual(advent_app.counter_label.text, "12")
            self.assertFalse(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "hours")
            self.assertEqual(advent_app.line_2_label.text, "until")

        with freezegun.freeze_time("2023-12-24 12:01:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertTrue(advent_app.counter_label.visible)
            self.assertEqual(advent_app.counter_label.text, "12")
            self.assertFalse(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "hours")
            self.assertEqual(advent_app.line_2_label.text, "until")

        with freezegun.freeze_time("2023-12-24 22:59:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertTrue(advent_app.counter_label.visible)
            self.assertEqual(advent_app.counter_label.text, "2")
            self.assertFalse(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "hours")
            self.assertEqual(advent_app.line_2_label.text, "until")

        with freezegun.freeze_time("2023-12-24 23:00:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertTrue(advent_app.counter_label.visible)
            self.assertEqual(advent_app.counter_label.text, "60")
            self.assertFalse(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "mins")
            self.assertEqual(advent_app.line_2_label.text, "until")

        with freezegun.freeze_time("2023-12-24 23:01:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertTrue(advent_app.counter_label.visible)
            self.assertEqual(advent_app.counter_label.text, "59")
            self.assertFalse(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "mins")
            self.assertEqual(advent_app.line_2_label.text, "until")

        with freezegun.freeze_time("2023-12-24 23:58:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertTrue(advent_app.counter_label.visible)
            self.assertEqual(advent_app.counter_label.text, "2")
            self.assertFalse(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "mins")
            self.assertEqual(advent_app.line_2_label.text, "until")

        with freezegun.freeze_time("2023-12-24 23:59:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertTrue(advent_app.counter_label.visible)
            self.assertEqual(advent_app.counter_label.text, "1")
            self.assertFalse(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "min")
            self.assertEqual(advent_app.line_2_label.text, "until")

        with freezegun.freeze_time("2023-12-25 00:00:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertFalse(advent_app.counter_label.visible)
            self.assertTrue(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "Merry")
            self.assertEqual(advent_app.line_2_label.text, "")

        with freezegun.freeze_time("2023-12-25 00:01:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertFalse(advent_app.counter_label.visible)
            self.assertTrue(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "Merry")
            self.assertEqual(advent_app.line_2_label.text, "")

        with freezegun.freeze_time("2023-12-25 23:59:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertFalse(advent_app.counter_label.visible)
            self.assertTrue(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "Merry")
            self.assertEqual(advent_app.line_2_label.text, "")

        with freezegun.freeze_time("2023-12-26 00:00:00"):
            advent_app.update_countdown()
            advent_app.update_view()
            self.assertTrue(advent_app.counter_label.visible)
            self.assertEqual(advent_app.counter_label.text, "365")
            self.assertFalse(advent_app.is_christmas)
            self.assertEqual(advent_app.line_1_label.text, "days")
            self.assertEqual(advent_app.line_2_label.text, "until")

    def test_determine_light_patterns_and_color(self):
        logger = logging.getLogger("TestAdventApp.test_determine_light_patterns_and_color")
        resource_path = os.path.join(os.path.dirname(__file__), "../examples")
        advent_app = AdventApp(font_path=os.path.join(resource_path, "fonts"),
                               image_path=os.path.join(resource_path, "images"))
        distinct_patterns = set()
        for i in range(0, 24):
            advent_app.determine_light_patterns_and_color(i)
            logger.debug(f"Hour: {i}. Pattern: {advent_app.pattern_index}. Color: {advent_app.colors_index}. "
                         f"Twinkle: {advent_app.twinkle}")
            distinct_patterns.add((advent_app.pattern_index, advent_app.colors_index, advent_app.twinkle))

        self.assertEqual(12, len(distinct_patterns))
