from lmae_module import AppModule
import time
import json
from threading import Lock
from vx_wx.vx_client import get_current_conditions_by_zipcode
from lmae_core import Stage, Text, Line, SpriteImage
from PIL import Image, ImageFont


class WeatherApp(AppModule):
    """
    Display the current weather
    """

    def __init__(self, api_key: str, zipcode: str):
        super().__init__()
        self.fresh_weather_data = False
        self.api_key = api_key
        self.zipcode = zipcode
        self.logger.info(f"Checking weather for ZIP code {self.zipcode}")
        self.running = False
        self.lock = Lock()
        self.stage : Stage = None
        self.actors = list()
        self.pre_render_callback = None
        self.current_conditions = None
        self.call_status = "ok"
        # self.temperature_font = ImageFont.truetype("fonts/press-start-2p-font/PressStart2P-vaV7.ttf", 8)
        self.temperature_font = ImageFont.truetype("fonts/Roboto/Roboto-Light.ttf", 18)
        self.temperature_label : Text = None
        self.daytime_image : SpriteImage = None
        self.moon_phase_image: SpriteImage = None
        self.timer_line : Line = None
        self.refresh_time = 900  # 900 seconds = 15 minutes

    # noinspection PyBroadException
    def get_current_conditions(self):
        try:
            self.logger.debug(f"Fetching current conditions for ZIP code {self.zipcode}")
            current_conditions = get_current_conditions_by_zipcode(self.zipcode, self.api_key)
            if current_conditions:
                self.logger.debug("Call to get conditions succeeded")
                self.current_conditions = current_conditions
                self.call_status = "ok"
                self.fresh_weather_data = True
            else:
                self.logger.error("Call to get conditions did not return any conditions")
                self.call_status = "error"
                # old conditions remain available

        except:
            self.logger.error("Call to get weather status failed")

    def compose_view(self):
        self.stage = Stage(matrix=self.matrix, matrix_options=self.matrix_options)

        # temperature actor
        self.temperature_label = Text(name='temperature', position=(5, 5), font=self.temperature_font,
                                      color=(255, 255, 255, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)
        self.stage.actors.append(self.temperature_label)

        # conditions image actor
        sprite_sheet = Image.open("images/weather-sprites.png").convert('RGBA')
        with open("images/weather-sprites.json") as spec_file:
            sprite_spec = json.load(spec_file)
        self.daytime_image = SpriteImage(name='daytime-condition', position=(39, 7), sheet=sprite_sheet, spec=sprite_spec)
        self.stage.actors.append(self.daytime_image)

        # moon phase actor
        self.moon_phase_image = SpriteImage(name='moon-phase', position=(39, 7), sheet=sprite_sheet, spec=sprite_spec)
        self.stage.actors.append(self.moon_phase_image)

        # timer actor
        self.timer_line = Line(name='timer-line', start=(0, 31), end=(63, 31), color=(255, 255, 0, 128))
        self.stage.actors.append(self.timer_line)

    def update_view(self, elapsed_time: float):
        # temperature
        temperature = f"{round(self.current_conditions['currentConditions']['temp'])}º"
        # self.logger.debug(f"Current temperature: {temperature}")
        self.temperature_label.text = str(temperature)

        # figure out whether it is day or night
        time_of_day = time.strftime("%H:%M:%S", time.localtime())
        sunrise = self.current_conditions['currentConditions']['sunrise']
        sunset = self.current_conditions['currentConditions']['sunset']
        is_daytime = sunrise < time_of_day < sunset
        if self.fresh_weather_data: self.logger.debug(f"Sunrise: {sunrise}, sunset: {sunset}, time of day: {time_of_day}")
        if self.fresh_weather_data: self.logger.debug(f"Is is daytime? {is_daytime}")

        # conditions
        # sprite names for conditions we can show
        # "sunny"  "cloudy" "rainy"  "lightning"  "snowflake-large" "snowflake-small"
        #   "foggy" "windy"

        if is_daytime:
            self.daytime_image.show()
            condition_sprite = None
            condition_str = self.current_conditions['currentConditions']['conditions']
            if self.fresh_weather_data: self.logger.debug(f'Current conditions from wx: {condition_str}')
            if condition_str in ['clear', 'type_43']:
                condition_sprite = 'sunny'
            elif condition_str == 'overcast':
                condition_sprite = 'cloudy'
            elif condition_str == 'rainy':
                condition_sprite = 'cloudy'
            if self.fresh_weather_data: self.logger.debug(f"Selected conditions sprite: {condition_sprite}")
            self.daytime_image.set_sprite(condition_sprite)
        else:
            if self.fresh_weather_data: self.logger.debug("Not showing daytime conditions")
            self.daytime_image.hide()

        # moon phase
        if not is_daytime:
            moon_phase_num = self.current_conditions['currentConditions']['moonphase']
            moon_phase_name = None
            if moon_phase_num > 0.9375:
                moon_phase_name = "moon-new"
            elif moon_phase_num > 0.8125:
                moon_phase_name = "moon-waning-crescent"
            elif moon_phase_num > 0.6875:
                moon_phase_name = "moon-waning-half"
            elif moon_phase_num > 0.5625:
                moon_phase_name = "moon-waning-gibbous"
            elif moon_phase_num > 0.4375:
                moon_phase_name = "moon-full"
            elif moon_phase_num > 0.3125:
                moon_phase_name = "moon-waxing-gibbous"
            elif moon_phase_num > 0.1875:
                moon_phase_name = "moon-waxing-half"
            elif moon_phase_num > 0.0625:
                moon_phase_name = "moon-waxing-crescent"
            else:
                moon_phase_name = "moon-new"

            if self.fresh_weather_data: self.logger.debug(f"Showing moon phase {moon_phase_num} as {moon_phase_name}")
            self.moon_phase_image.show()
            self.moon_phase_image.set_sprite(moon_phase_name)
        else:
            if self.fresh_weather_data: self.logger.debug(f"Not showing moon phase")
            self.moon_phase_image.hide()

        # timer line, shows remaining time until next call to refresh weather data
        old_size = self.timer_line.size
        relative_length = int(round(max(round(self.refresh_time - elapsed_time), 0) * 64.0 / self.refresh_time))
        self.timer_line.set_start((64-relative_length, 31))

        if old_size[0] != self.timer_line.size[0]:
            self.logger.debug(f"Timer line length is now {relative_length}")

        self.timer_line.set_color((255, 255, 0, 128) if is_daytime else (0, 0, 255, 128))

        self.fresh_weather_data = False

    def prepare(self):
        self.compose_view()

    def run(self):
        self.logger.debug("Run started")
        self.running = True
        self.compose_view()
        frame_number = 0

        try:
            while self.running:
                # get updated weather conditions
                self.get_current_conditions()

                # update the view
                self.update_view(0)
                self.stage.render_frame(frame_number)
                frame_number += 1

                # wait 15 minutes
                waiting = True
                wait_start = time.time()
                self.logger.debug(f"Waiting {self.refresh_time / 60} minutes to refresh weather data")
                while waiting and self.running:
                    time.sleep(1)
                    current_time = time.time()
                    elapsed_time = current_time - wait_start
                    self.update_view(elapsed_time)
                    self.stage.needs_render = True # have to force this for some reason
                    self.stage.render_frame(frame_number)
                    frame_number += 1
                    waiting = elapsed_time < self.refresh_time

        finally:
            self.logger.debug("Run stopped")

    def stop(self):
        self.logger.debug("Got command to stop")
        self.running = False
