import asyncio
import time
import json

from datetime import datetime
from PIL import Image, ImageFont

from openweather.openweather_client import get_conditions_and_forecast_by_lat_long
from lmae_core import Stage
from lmae_module import AppModule
from lmae_actor import SpriteImage, Text, Line
from lmae_animation import Easing
from lmae_component import Carousel

TOK_LAT = '39.0158678'
TOK_LONG = '-77.0734945'


class WeatherApp(AppModule):
    """
    Display the current weather
    """

    # noinspection PyTypeChecker
    def __init__(self, api_key: str, latitude: str = TOK_LAT, longitude: str = TOK_LONG):
        super().__init__()
        self.fresh_weather_data = False
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude
        self.logger.info(f"Weather conditions for location at lat/long {self.latitude}, {self.longitude}")
        self.lock = asyncio.Lock()
        self.stage: Stage = None
        self.actors = list()
        self.pre_render_callback = None
        self.conditions_and_forecast = None
        self.call_status = "ok"
        self.primary_text_font = ImageFont.truetype("fonts/Roboto/Roboto-Light.ttf", 16)
        self.temperature_label: Text = None
        self.secondary_text_font = ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5)
        self.dewpoint_label: Text = None
        self.feels_like_label: Text = None
        self.humidity_label: Text = None
        self.low_temp_label: Text = None
        self.high_temp_label: Text = None
        self.temps_carousel: Carousel = None

        self.temperature_str: str = None
        self.dewpoint_str: str = None
        self.feels_like_str: str = None
        self.humidity_str: str = None
        self.low_temp_str: str = None
        self.high_temp_str: str = None
        self.sunrise: int = None
        self.sunset: int = None
        self.condition_str: str = None
        self.condition_code: int = None
        self.moon_phase_num: float = None

        self.daytime_image: SpriteImage = None
        self.moon_phase_image: SpriteImage = None
        self.timer_line: Line = None
        self.refresh_time = 900  # 900 seconds = 15 minutes

    def compose_view(self):
        self.stage = Stage(matrix=self.matrix, matrix_options=self.matrix_options)

        # temperature actor
        self.temperature_label = Text(name='TemperatureActor', position=(5, 5), font=self.primary_text_font,
                                      color=(255, 255, 255, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)
        self.stage.actors.append(self.temperature_label)

        # feels like actor
        self.feels_like_label = Text(name='FeelsLikeActor', position=(5, 23), font=self.secondary_text_font,
                                     color=(224, 224, 224, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)

        # dewpoint actor
        self.dewpoint_label = Text(name='DewpointActor', position=(5, 23), font=self.secondary_text_font,
                                   color=(224, 224, 224, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)

        # humidity actor
        self.humidity_label = Text(name='HumidityActor', position=(5, 23), font=self.secondary_text_font,
                                   color=(224, 224, 224, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)

        # low temp actor
        self.low_temp_label = Text(name='LowTempActor', position=(5, 23), font=self.secondary_text_font,
                                   color=(224, 224, 224, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)

        # high temp actor
        self.high_temp_label = Text(name='HighTempActor', position=(5, 23), font=self.secondary_text_font,
                                    color=(224, 224, 224, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)

        # carousel for temps
        self.temps_carousel = Carousel(name='TempsCarousel', crop_area=(5, 23, 38, 30), easing=Easing.BEZIER,
                                       position=(5, 23),
                                       panels=[self.feels_like_label, self.dewpoint_label, self.humidity_label,
                                               self.low_temp_label, self.high_temp_label])
        self.stage.actors.append(self.temps_carousel)
        self.stage.add_animations(self.temps_carousel.get_animations())
        self.logger.debug(f"Stage has {len(self.stage.animations)} animations")

        # conditions image actor
        sprite_sheet = Image.open("images/weather-sprites.png").convert('RGBA')
        with open("images/weather-sprites.json") as spec_file:
            sprite_spec = json.load(spec_file)
        self.daytime_image = SpriteImage(name='daytime-condition', position=(39, 7), sheet=sprite_sheet,
                                         spec=sprite_spec)
        self.stage.actors.append(self.daytime_image)

        # moon phase actor
        self.moon_phase_image = SpriteImage(name='moon-phase', position=(39, 7), sheet=sprite_sheet, spec=sprite_spec)
        self.stage.actors.append(self.moon_phase_image)

        # timer actor
        self.timer_line = Line(name='timer-line', start=(0, 31), end=(63, 31), color=(255, 255, 0, 128))
        self.stage.actors.append(self.timer_line)

    # noinspection PyBroadException
    def update_weather_data(self):
        try:
            self.logger.debug(f"Fetching current weather data")
            conditions_and_forecast = get_conditions_and_forecast_by_lat_long(self.latitude, self.longitude,
                                                                              self.api_key)
            if conditions_and_forecast:
                self.logger.debug("Call to get conditions and forecast succeeded")
                self.conditions_and_forecast = conditions_and_forecast
                self.call_status = "ok"
                self.fresh_weather_data = True

                # set up weather values
                """
                # VisualCrossing API response format
                self.temperature_str = f"{round(conditions_and_forecast['currentConditions']['temp'])}º"
                self.dewpoint_str = f"Dew {round(self.conditions_and_forecast['currentConditions']['dew'])}º"
                self.feels_like_str = f"FL {round(self.conditions_and_forecast['currentConditions']['feelslike'])}º"
                self.low_temp_str = f"Low {round(self.conditions_and_forecast['days'][0]['tempmin'])}º"
                self.high_temp_str = f"Hi {round(self.conditions_and_forecast['days'][0]['tempmax'])}º"
                self.moon_phase_num = self.conditions_and_forecast['currentConditions']['moonphase']
                forecast_date_time = datetime.fromtimestamp(self.conditions_and_forecast['days'][0]['datetimeEpoch'])
                """

                # OpenWeather API response format
                self.temperature_str = f"{round(conditions_and_forecast['current']['temp'])}º"
                self.feels_like_str = f"FL {round(self.conditions_and_forecast['current']['feels_like'])}º"
                self.dewpoint_str = f"Dew {round(self.conditions_and_forecast['current']['dew_point'])}º"
                self.humidity_str = f"RH {round(self.conditions_and_forecast['current']['humidity'])}%"
                self.low_temp_str = f"Low {round(self.conditions_and_forecast['daily'][0]['temp']['min'])}º"
                self.high_temp_str = f"Hi {round(self.conditions_and_forecast['daily'][0]['temp']['max'])}º"
                self.sunrise = self.conditions_and_forecast['current']['sunrise']
                self.sunset = self.conditions_and_forecast['current']['sunset']
                self.condition_code = self.conditions_and_forecast['current']['weather'][0]['id']
                self.condition_str = self.conditions_and_forecast['current']['weather'][0]['main'].lower()
                self.moon_phase_num = self.conditions_and_forecast['daily'][0]['moon_phase']
                forecast_date_time = datetime.fromtimestamp(self.conditions_and_forecast['daily'][0]['dt'])

                # log
                self.logger.debug(f"    Temperature : {self.temperature_str}")
                self.logger.debug(f"    Feels like  : {self.feels_like_str}")
                self.logger.debug(f"    Dewpoint    : {self.dewpoint_str}")
                self.logger.debug(f"    Humidity    : {self.humidity_str}")
                self.logger.debug(f"    Low temp    : {self.low_temp_str}")
                self.logger.debug(f"    High temp   : {self.high_temp_str}")
                self.logger.debug(f" Forecast date  : {forecast_date_time}")

            else:
                self.logger.error("Call to get weather data failed")
                self.call_status = "error"
                self.fresh_weather_data = False
                # old conditions remain available

        except:
            self.logger.exception("Call to get weather status failed")

    @staticmethod
    def format_epoch_time(timestamp):
        timestamp_format = "%H:%M:%S"
        if timestamp is str:
            timestamp = float(timestamp)
        return time.strftime(timestamp_format, time.localtime(timestamp))

    def update_view(self, elapsed_time: float):
        self.temperature_label.text = self.temperature_str
        self.dewpoint_label.text = self.dewpoint_str
        self.feels_like_label.text = self.feels_like_str
        self.humidity_label.text = self.humidity_str
        self.low_temp_label.text = self.low_temp_str
        self.high_temp_label.text = self.high_temp_str

        # figure out whether it is day or night
        # time_of_day = time.strftime(timestamp_format, time.localtime())
        time_of_day = time.time()
        # self.logger.debug(f"RAW: Sunrise: {self.sunrise}, sunset: {self.sunset}, time of day: {time_of_day}")
        is_daytime = self.sunrise < time_of_day < self.sunset
        sunrise_str = self.format_epoch_time(self.sunrise)
        sunset_str = self.format_epoch_time(self.sunset)
        tod_str = self.format_epoch_time(time_of_day)
        # if self.fresh_weather_data:
        #    self.logger.debug(f"Sunrise: {sunrise_str}, sunset: {sunset_str}, time of day: {tod_str}")
        # if self.fresh_weather_data:
        #    self.logger.debug(f"Is is daytime? {is_daytime}")

        # conditions
        # sprite names for conditions we can show
        # "sunny"  "cloudy" "rainy"  "lightning"  "snowflake-large" "snowflake-small"
        #   "foggy" "windy"

        if is_daytime:
            self.daytime_image.show()
            condition_sprite = None
            # if self.fresh_weather_data: self.logger.debug(f'Current conditions from wx: {self.condition_str}')

            # VX interpretation
            """
            if self.condition_str in ['clear', 'type_43']:
                condition_sprite = 'sunny'
            elif self.condition_str in ['overcast', 'type_41', 'type_42']:
                condition_sprite = 'cloudy'
            elif self.condition_str in ['rainy', 'type_2', 'type_3', 'type_4', 'type_5', 'type_6', 'type_9', 'type_10',
                                   'type_11', 'type_13', 'type_14', 'type_20', 'type_21', 'type_22', 'type_23',
                                   'type_24', 'type_25', 'type_26', 'type_32', 'type_36', 'type_37', 'type_38']:
                condition_sprite = 'rainy'
            """

            # OW interpretation
            if 200 <= self.condition_code <= 299:
                condition_sprite = 'lightning'
            elif 300 <= self.condition_code <= 399:
                condition_sprite = 'rainy'
            elif 500 <= self.condition_code <= 599:
                condition_sprite = 'rainy'
            elif 500 <= self.condition_code <= 599:
                condition_sprite = 'snowflake-large'
            elif 700 <= self.condition_code <= 799:
                condition_sprite = 'foggy'
            elif 800 <= self.condition_code <= 802:
                condition_sprite = 'sunny'
            elif 803 <= self.condition_code <= 899:
                condition_sprite = 'cloudy'
            if self.fresh_weather_data: self.logger.debug(f"Selected conditions sprite: {condition_sprite}")
            self.daytime_image.set_sprite(condition_sprite)
        else:
            #if self.fresh_weather_data: self.logger.debug("Not showing daytime conditions")
            self.daytime_image.hide()

        # moon phase
        if not is_daytime:
            # moon_phase_name = None
            if self.moon_phase_num > 0.9375:
                moon_phase_name = "moon-new"
            elif self.moon_phase_num > 0.8125:
                moon_phase_name = "moon-waning-crescent"
            elif self.moon_phase_num > 0.6875:
                moon_phase_name = "moon-waning-half"
            elif self.moon_phase_num > 0.5625:
                moon_phase_name = "moon-waning-gibbous"
            elif self.moon_phase_num > 0.4375:
                moon_phase_name = "moon-full"
            elif self.moon_phase_num > 0.3125:
                moon_phase_name = "moon-waxing-gibbous"
            elif self.moon_phase_num > 0.1875:
                moon_phase_name = "moon-waxing-half"
            elif self.moon_phase_num > 0.0625:
                moon_phase_name = "moon-waxing-crescent"
            else:
                moon_phase_name = "moon-new"

            if self.fresh_weather_data:
                self.logger.debug(f"Showing moon phase {self.moon_phase_num} as {moon_phase_name}")
            self.moon_phase_image.show()
            self.moon_phase_image.set_sprite(moon_phase_name)
        else:
            if self.fresh_weather_data: self.logger.debug(f"Not showing moon phase")
            self.moon_phase_image.hide()

        # timer line, shows remaining time until next call to refresh weather data
        # old_size = self.timer_line.size
        relative_length = int(round(max(round(self.refresh_time - elapsed_time), 0) * 64.0 / self.refresh_time))
        self.timer_line.set_start((64-relative_length, 31))

        # if old_size[0] != self.timer_line.size[0]:
        #     self.logger.debug(f"Timer line length is now {relative_length}")

        self.timer_line.set_color((255, 255, 0, 128) if is_daytime else (0, 0, 255, 128))

        self.fresh_weather_data = False

    def prepare(self):
        self.compose_view()

    async def run(self):
        await super().run()
        self.logger.debug("Run started")
        # self.compose_view()
        max_frame_rate = 60
        min_time_per_frame = 1.0 / max_frame_rate

        try:
            while self.running:
                # get updated weather conditions
                self.update_weather_data()

                # update the view
                self.update_view(0)
                self.stage.render_frame()

                # wait 15 minutes
                waiting = True
                wait_start = time.time()
                self.logger.debug(f"Waiting {self.refresh_time / 60} minutes to refresh weather data")
                last_time = time.perf_counter()
                while waiting and self.running:
                    current_time = time.time()
                    elapsed_time = current_time - wait_start
                    self.update_view(elapsed_time)
                    self.stage.needs_render = True  # have to force this for some reason
                    self.stage.render_frame()
                    waiting = elapsed_time < self.refresh_time

                    # await asyncio.sleep(1)

                    # calculate the frame rate and render that
                    render_end_time = time.perf_counter()

                    # if we are rendering faster than max frame rate, slow down
                    elapsed_render_time = render_end_time - last_time
                    if elapsed_render_time < min_time_per_frame:
                        sleep_time = min_time_per_frame - elapsed_render_time
                        # self.logger.debug(f"Sleeping for {sleep_time}")
                        await asyncio.sleep(sleep_time)
                    else:
                        # gotta yield control, with minimal sleep amount
                        await asyncio.sleep(min_time_per_frame/10.0)

                    # mark the timestamp
                    last_time = time.perf_counter()

        finally:
            self.logger.debug("Run stopped")
