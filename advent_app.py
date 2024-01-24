import asyncio
import datetime
import os
import time

from datetime import datetime
from PIL import ImageFont

import app_runner
from lmae.animation import Sequence, HueFade
from lmae.core import Stage, Animation
from lmae.app import DisplayManagedApp
from lmae.actor import Rectangle, StillImage, Text


class AdventApp(DisplayManagedApp):
    """
    Display the number of days until Christmas weather
    """

    # noinspection PyTypeChecker
    def __init__(self, refresh_time: int = 60):
        super().__init__(refresh_time=refresh_time, max_frame_rate = 20)
        self.actors = list()
        self.pre_render_callback = None
        self.refresh_time = refresh_time
        self.big_font = ImageFont.truetype("fonts/Roboto/Roboto-Light.ttf", 15)
        self.counter_label = Text(font=self.big_font, name="counter", position=(8, 2))
        self.small_font = ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5)
        self.line_1_label = Text(font=self.small_font, name="line_1_text", position=(9, 18), text="days",
                                 color=(192, 192, 192, 255))
        self.line_2_label = Text(font=self.small_font, name="line_2_text", position=(7, 25), text="until",
                                 color=(192, 192, 192, 255))
        self.tree_image = StillImage(name="tree", position=(37, 0))
        self.tree_image.set_from_file('images/pixel-tree-22x32-alpha.png')
        self.days_until_christmas = 0
        self.hours_until_christmas = 0
        self.minutes_until_christmas = 0
        self.is_christmas = False

        self.was_it_christmas = None
        self.last_days_until_christmas = -1
        self.last_hours_until_christmas = -1
        self.last_minutes_until_christmas = -1

        self.pattern_index = 0
        self.colors_index = 0
        self.twinkle = False
        self.last_hour = -1

        self.colors = []
        self.pattern = []

        self.lights_locations: list[tuple[int, int]] = list()
        self.lights_list: list[Rectangle] = list()
        self.find_the_tree_lights()

    def find_the_tree_lights(self):
        pil_image = self.tree_image.image
        offset = self.tree_image.position
        self.lights_locations.clear()
        for y in range(0, self.tree_image.size[1]):
            for x in range(0, self.tree_image.size[0]):
                pixel_color = pil_image.getpixel((x, y))
                if pixel_color == (255, 255, 255) or pixel_color == (255, 255, 255, 255):
                    self.lights_locations.append((x + offset[0], y + offset[1]))

        self.logger.debug(f"Found {len(self.lights_locations)} lights on tree")

        self.lights_list.clear()
        light_ctr = 0
        for location in self.lights_locations:
            light_ctr = light_ctr + 1
            light = Rectangle(name=f"Light_{light_ctr}", position=location, size=(0, 0), color=(192, 192, 255, 255))
            self.lights_list.append(light)

    def prepare(self):
        super().prepare()
        self.stage.actors.extend((self.line_1_label, self.line_2_label, self.counter_label, self.tree_image))
        self.stage.actors.extend(self.lights_list)

    def update_countdown(self):
        current_datetime = datetime.now()
        current_day = current_datetime.day
        current_month = current_datetime.month
        current_year = current_datetime.year
        # self.logger.debug(f"Current date: {current_year:04}-{current_month:02}-{current_day:02}")
        self.is_christmas = current_month == 12 and current_day == 25
        christmas_has_passed = current_month == 12 and current_day > 25
        # self.logger.debug(f"Has Christmas passed this year already? {'yes' if christmas_has_passed else 'no'}")

        christmas_datetime = datetime(current_year + 1 if christmas_has_passed else current_year, 12, 25, 0, 0)
        # self.logger.debug(f"Date of Christmas: {christmas_datetime.year:04}-"
        #                   f"{christmas_datetime.month:02}-{christmas_datetime.day:02}")

        christmas_delta = christmas_datetime - current_datetime
        days_until = christmas_delta.days
        if christmas_delta.seconds > 0:
            days_until = days_until + 1
        self.days_until_christmas = days_until
        if self.days_until_christmas <= 1:
            self.hours_until_christmas = 24 - current_datetime.hour
            self.minutes_until_christmas = 60 - current_datetime.minute

        if self.last_days_until_christmas != self.days_until_christmas:
            self.logger.debug(f"Counted {self.days_until_christmas} days until Christmas")

    @staticmethod
    def format_epoch_time(timestamp):
        timestamp_format = "%H:%M:%S"
        if timestamp is str:
            timestamp = float(timestamp)
        return time.strftime(timestamp_format, time.localtime(timestamp))

    def determine_light_patterns_and_color(self, hour_of_day: int):
        self.pattern_index = int(hour_of_day / 6) % 2
        self.colors_index = int(hour_of_day % 6)
        self.twinkle = int(hour_of_day % 2)

    def update_view(self, elapsed_time: float = 0.0):
        self.update_countdown()

        # determine counter and text label values
        if (self.was_it_christmas != self.is_christmas or self.last_days_until_christmas != self.days_until_christmas or
                self.last_hours_until_christmas != self.hours_until_christmas or
                self.last_minutes_until_christmas != self.minutes_until_christmas):
            self.counter_label.show()
            self.line_2_label.set_text("until")
            if self.is_christmas:
                self.counter_label.hide()
                self.line_1_label.set_text("Merry")
                self.line_2_label.set_text("")
            elif self.days_until_christmas == 1:
                if self.hours_until_christmas <= 1:
                    if self.minutes_until_christmas == 1:
                        self.line_1_label.set_text("min")
                    else:
                        self.line_1_label.set_text("mins")
                    self.counter_label.set_text(str(self.minutes_until_christmas))
                else:
                    if self.hours_until_christmas == 1:
                        self.line_1_label.set_text("hour")
                    else:
                        self.line_1_label.set_text("hours")
                    self.counter_label.set_text(str(self.hours_until_christmas))
            else:  # days
                self.counter_label.set_text(str(self.days_until_christmas))
                self.line_1_label.set_text("days")

            # center labels
            counter_x_offset = int((32 - self.counter_label.size[0]) / 2)
            line_1_x_offset = int((32 - self.line_1_label.size[0]) / 2)
            line_2_x_offset = int((32 - self.line_2_label.size[0]) / 2)
            self.counter_label.set_position((counter_x_offset, 2))
            self.line_1_label.set_position((line_1_x_offset, 18))
            self.line_2_label.set_position((line_2_x_offset, 25))

        self.was_it_christmas = self.is_christmas
        self.last_days_until_christmas = self.days_until_christmas
        self.last_hours_until_christmas = self.hours_until_christmas
        self.last_minutes_until_christmas = self.minutes_until_christmas

        # determine Christmas light pattern and colors
        hour_of_day = datetime.now().hour
        if hour_of_day != self.last_hour:
            self.last_hour = hour_of_day
            self.stage.clear_animations_for_all(self.lights_list)
            self.determine_light_patterns_and_color(hour_of_day)
            if self.colors_index == 0:  # 1 color:  white
                self.colors = [(255, 255, 255, 255)]
            elif self.colors_index == 1:  # 2 colors: red blue
                self.colors = [(255, 0, 0, 255), (0, 0, 255, 255)]
            elif self.colors_index == 2:  # 2 colors: red white
                self.colors = [(255, 0, 0, 255), (255, 255, 255, 255)]
            elif self.colors_index == 3:  # 3 colors: red white blue
                self.colors = [(255, 0, 0, 255), (255, 255, 255, 255), (0, 0, 255, 255)]
            elif self.colors_index == 4:  # 3 colors: purple, yellowish green, aqua
                self.colors = [(255, 0, 189, 255), (189, 255, 0, 255), (0, 189, 255, 255)]
            elif self.colors_index == 5:  # 4 colors: red, green, blue purple
                self.colors = [(255, 0, 0, 255), (128, 255, 0, 255), (0, 255, 255, 255), (128, 0, 255, 255)]

            self.logger.debug(f"Using color option {self.colors_index} with {len(self.colors)} colors")
            self.logger.debug(f"Twinkle is set to {self.twinkle}")

            tree_color = (65, 167, 66, 255)
            light_duration = 1.0  # seconds
            light_sequences: list[Animation] = []
            if self.pattern_index == 0:  # on/off  (alt with tree green, alt every other)
                self.logger.debug("Using pattern 0: alternate on/off")
                ci = 0  # color offset index
                li = 0  # light index
                for light in self.lights_list:
                    sequence = Sequence(name=f"Light_{li}_sequence", actor=light, repeat=True)
                    if li % 2 == 0:  # start off vs start on
                        start_color = tree_color
                        end_color = self.colors[ci] if self.twinkle else tree_color
                    else:
                        start_color = self.colors[ci]
                        end_color = tree_color if self.twinkle else self.colors[ci]

                    hue_fade = HueFade(name=f"Light{li}_fade_0", actor=light, initial_color=start_color,
                                       final_color=end_color, callback=light.set_color, duration=light_duration)
                    sequence.add_animations(hue_fade)

                    if li % 2 == 0:  # start off vs start on
                        start_color = self.colors[ci]
                        end_color = tree_color if self.twinkle else self.colors[ci]
                    else:
                        start_color = tree_color
                        end_color = self.colors[ci] if self.twinkle else tree_color

                    hue_fade = HueFade(name=f"Light{li}_fade_1", actor=light, initial_color=start_color,
                                       final_color=end_color, callback=light.set_color, duration=light_duration)
                    sequence.add_animations(hue_fade)

                    ci = (ci + 1) % len(self.colors)
                    li = li + 1
                    light_sequences.append(sequence)
            else:  # chase
                self.logger.debug("Using pattern 1: color chase")
                li = 0  # light index
                for light in self.lights_list:
                    sequence = Sequence(name=f"Light_{li}_sequence", actor=light, repeat=True)
                    for i in range(0, len(self.colors)):
                        ci = (li + i) % len(self.colors)
                        start_color = self.colors[ci]
                        end_color = self.colors[(ci + 1) % len(self.colors)] if self.twinkle else start_color
                        hue_fade = HueFade(name=f"Light{li}_fade_{i}", actor=light, initial_color=start_color,
                                           final_color=end_color, callback=light.set_color, duration=light_duration)
                        sequence.add_animations(hue_fade)
                    li = li + 1
                    light_sequences.append(sequence)
            self.stage.add_animations(light_sequences)


if __name__ == "__main__":
    app_runner.start_app(AdventApp())
