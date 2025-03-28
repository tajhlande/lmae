import asyncio
import json
import os.path
import time

from datetime import datetime
from PIL import Image, ImageFont, ImageFilter, ImageEnhance

from context import lmae
from lmae import app_runner
from openweather.openweather_client import get_conditions_and_forecast_by_lat_long
from lmae.app import DisplayManagedApp
from lmae.actor import StillImage, SpriteImage, Text, Line
from lmae.animation import Easing, Sequence, Still, StraightMove
from lmae.component import Carousel


class WeatherApp(DisplayManagedApp):
    """
    Display the current weather
    """

    # noinspection PyTypeChecker
    def __init__(self, api_key: str, latitude: str, longitude: str, refresh_time: int = 900, resource_path: str = ""):
        super().__init__(max_frame_rate=60, refresh_time=refresh_time)
        self.resource_path = resource_path
        self.fresh_weather_data = False
        self.last_weather_data_at: float = None
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude
        self.logger.info(f"Weather conditions for location at lat/long {self.latitude}, {self.longitude}")
        self.lock = asyncio.Lock()
        self.actors = list()
        self.pre_render_callback = None
        self.conditions_and_forecast = None
        self.call_status = "ok"
        self.primary_text_font = ImageFont.truetype(os.path.join(resource_path, "fonts/Roboto/Roboto-Light.ttf"), 15)
        self.temperature_label: Text = None
        self.secondary_text_font = ImageFont.truetype(os.path.join(resource_path,
                                                                   "fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf"), 5)
        self.dewpoint_label: Text = None
        self.feels_like_label: Text = None
        self.humidity_label: Text = None
        self.low_temp_label: Text = None
        self.high_temp_label: Text = None
        self.temps_carousel: Carousel = None
        self.background_image: StillImage = None
        self.condition_description_label: Text = None

        self.temperature_str: str = None
        self.dewpoint_str: str = None
        self.feels_like_str: str = None
        self.humidity_str: str = None
        self.low_temp_str: str = None
        self.high_temp_str: str = None
        self.sunrise: int = None
        self.sunset: int = None
        self.condition_code: int = None
        self.condition_short_desc: str = None
        self.condition_long_desc: str = None
        self.condition_short_desc_list: list[str] = []
        self.condition_long_desc_list: list[str] = []
        self.combined_short_desc: str = None
        self.combined_long_desc: str = None
        self.condition_description_label_position: tuple[int, int] = None
        self.need_to_update_condition_desc_animation: bool = True
        self.moon_phase_num: float = None
        self.is_daytime: bool = None
        self.moonrise: int = None
        self.moonset: int = None
        self.is_moon_out: bool = None

        self.main_daytime_image: SpriteImage = None
        self.daytime_image_shadow: SpriteImage = None
        self.support_daytime_image_1: SpriteImage = None
        self.support_daytime_image_2: SpriteImage = None
        self.moon_phase_image: SpriteImage = None
        self.timer_line: Line = None
        self.refresh_time: int = refresh_time  # 900 seconds = 15 minutes
        self.logger.info(f"Refreshing weather data every {self.refresh_time} seconds")
        self.old_brightness: int = None

        self.blue_sky_image = (Image.open(os.path.join(resource_path, "images/backgrounds/blue_sky.png"))
                                    .convert('RGBA'))
        self.cloudy_image = (Image.open(os.path.join(resource_path, "images/backgrounds/cloudy.png"))
                                  .convert('RGBA'))
        self.dark_clouds_image = (Image.open(os.path.join(resource_path, "images/backgrounds/dark_clouds.png"))
                                       .convert('RGBA'))
        self.night_sky_image = (Image.open(os.path.join(resource_path, "images/backgrounds/night_sky.png"))
                                     .convert('RGBA'))
        self.sunrise_sunset_image = (Image.open(os.path.join(resource_path, "images/backgrounds/sunrise_sunset.png"))
                                          .convert('RGBA'))
        self.bg_image_name = None

        # moved actor setup from prepare() since it can really just be done once

        # background image
        self.background_image = StillImage(name='BackgroundImage', position=(0, 0))

        # temperature actor
        self.temperature_label = Text(name='TemperatureActor', position=(5, 7), font=self.primary_text_font,
                                      color=(255, 255, 255, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)

        # feels like actor
        self.feels_like_label = Text(name='FeelsLikeActor', position=(5, 24), font=self.secondary_text_font,
                                     color=(224, 224, 224, 255), stroke_color=(0, 0, 0, 220), stroke_width=1)

        # dewpoint actor
        self.dewpoint_label = Text(name='DewpointActor', position=(5, 24), font=self.secondary_text_font,
                                   color=(224, 224, 224, 255), stroke_color=(0, 0, 0, 220), stroke_width=1)

        # humidity actor
        self.humidity_label = Text(name='HumidityActor', position=(5, 24), font=self.secondary_text_font,
                                   color=(224, 224, 224, 255), stroke_color=(0, 0, 0, 220), stroke_width=1)

        # low temp actor
        self.low_temp_label = Text(name='LowTempActor', position=(5, 24), font=self.secondary_text_font,
                                   color=(224, 224, 224, 255), stroke_color=(0, 0, 0, 220), stroke_width=1)

        # high temp actor
        self.high_temp_label = Text(name='HighTempActor', position=(5, 24), font=self.secondary_text_font,
                                    color=(224, 224, 224, 255), stroke_color=(0, 0, 0, 220), stroke_width=1)

        # carousel for temps
        self.temps_carousel = Carousel(name='TempsCarousel', crop_area=(4, 23, 38, 31), easing=Easing.BEZIER,
                                       position=(4, 23), panel_offset=(1, 1),
                                       panels=[self.feels_like_label, self.dewpoint_label, self.humidity_label,
                                               self.low_temp_label, self.high_temp_label])

        # condition description actor
        self.condition_description_label_position = (2, 2)
        self.condition_description_label = Text(name='condition-description',
                                                position=self.condition_description_label_position,
                                                font=self.secondary_text_font, stroke_width=1,
                                                color=(192, 192, 192, 255), stroke_color=(0, 0, 0, 220))

        # conditions image actor
        sprite_sheet: Image = Image.open(os.path.join(self.resource_path, "images/weather-sprites.png")).convert('RGBA')
        with open(os.path.join(self.resource_path, "images/weather-sprites.json")) as spec_file:
            sprite_spec = json.load(spec_file)
        self.main_daytime_image = SpriteImage(name='main-daytime-condition', position=(39, 10),
                                              sheet=sprite_sheet, spec=sprite_spec)
        self.support_daytime_image_1 = SpriteImage(name='support-daytime-condition-1', position=(39, 10),
                                                   sheet=sprite_sheet, spec=sprite_spec)
        self.support_daytime_image_2 = SpriteImage(name='support-daytime-condition-2', position=(39, 10),
                                                   sheet=sprite_sheet, spec=sprite_spec)

        # set up outline shadow for these sprites
        sprite_grayscale = sprite_sheet.copy().convert('L')

        # Detect edges
        edges = sprite_grayscale.filter(ImageFilter.FIND_EDGES)

        # Make fatter, smoother edges
        edges = edges.filter(ImageFilter.MaxFilter(3))
        # Make very fat edges
        # edges = edges.filter(ImageFilter.MaxFilter(7))
        enhancer = ImageEnhance.Brightness(edges)
        # to reduce brightness by 50%, use factor 0.5
        edges = enhancer.enhance(0.4)
        edges = edges.filter(ImageFilter.GaussianBlur(0.5))

        # convert edges into shadow image by applying edges as alpha to black image
        shadow_image = Image.new("RGBA", sprite_grayscale.size, (0, 0, 0, 255))
        shadow_image.putalpha(edges)
        self.daytime_image_shadow = SpriteImage(name='daytime-condition-shadow',
                                                position=self.main_daytime_image.position,
                                                sheet=shadow_image, spec=sprite_spec)


        # moon phase actor
        self.moon_phase_image = SpriteImage(name='moon-phase', position=(39, 7), sheet=sprite_sheet, spec=sprite_spec)


        # timer actor
        self.timer_line = Line(name='timer-line', start=(0, 31), end=(63, 31), color=(255, 255, 0, 128))



    def prepare(self):
        super().prepare()

        self.stage.animations.clear()
        self.stage.actors.clear()

        self.stage.actors.append(self.background_image)
        self.stage.actors.append(self.temperature_label)
        self.stage.actors.append(self.temps_carousel)
        self.stage.add_animations(self.temps_carousel.get_animations())
        self.logger.debug(f"Stage has {len(self.stage.animations)} animations")
        self.stage.actors.append(self.condition_description_label)
        self.stage.actors.append(self.daytime_image_shadow)
        self.stage.actors.append(self.main_daytime_image)
        self.stage.actors.append(self.moon_phase_image)
        self.stage.actors.append(self.support_daytime_image_1)
        self.stage.actors.append(self.support_daytime_image_2)
        self.stage.actors.append(self.timer_line)

        self.need_to_update_condition_desc_animation = True


# noinspection PyBroadException
    def update_weather_data(self):
        try:
            self.logger.debug(f"Fetching current weather data")

            # by setting this before the call, we avoid repeated calls in the case of errors
            # as long as the temperature was retrieved at least once, we won't exceed our call count
            self.last_weather_data_at = time.time()

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
                self.condition_short_desc = self.conditions_and_forecast['current']['weather'][0]['main']
                self.condition_long_desc = self.conditions_and_forecast['current']['weather'][0]['description']
                forecast_date_time = datetime.fromtimestamp(self.conditions_and_forecast['daily'][0]['dt'])
                self.is_daytime = None
                self.condition_short_desc_list = [item['main'] for item in
                                                  self.conditions_and_forecast['current']['weather']]
                self.condition_long_desc_list = [item['description'] for item in
                                                 self.conditions_and_forecast['current']['weather']]
                self.combined_short_desc = ', '.join(self.condition_short_desc_list)
                self.combined_long_desc = ', '.join(self.condition_long_desc_list)
                self.need_to_update_condition_desc_animation = True

                self.moon_phase_num = self.conditions_and_forecast['daily'][0]['moon_phase']
                self.moonrise = self.conditions_and_forecast['daily'][0]['moonrise']
                self.moonset = self.conditions_and_forecast['daily'][0]['moonset']
                self.is_moon_out = None

                # log
                self.logger.debug(f"      Condition code : {self.condition_code}")
                self.logger.debug(f"    First short desc : {self.condition_short_desc}")
                self.logger.debug(f"     First long desc : {self.condition_long_desc}")
                self.logger.debug(f" Combined short desc : {self.combined_short_desc}")
                self.logger.debug(f"  Combined long desc : {self.combined_long_desc}")
                self.logger.debug(f"         Temperature : {self.temperature_str}")
                self.logger.debug(f"         Feels like  : {self.feels_like_str}")
                self.logger.debug(f"         Dewpoint    : {self.dewpoint_str}")
                self.logger.debug(f"         Humidity    : {self.humidity_str}")
                self.logger.debug(f"         Low temp    : {self.low_temp_str}")
                self.logger.debug(f"         High temp   : {self.high_temp_str}")
                self.logger.debug(f"      Forecast date  : {forecast_date_time}")
                self.logger.debug(f"      Moonrise       : {self.format_epoch_time(self.moonrise)}")
                self.logger.debug(f"      Moonset        : {self.format_epoch_time(self.moonset)}")

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
        time_since_last_update = time.time() - self.last_weather_data_at if self.last_weather_data_at \
            else self.refresh_time + 1
        if not self.temperature_str or time_since_last_update >= self.refresh_time:
            self.update_weather_data()

        self.temperature_label.set_text(self.temperature_str)
        self.dewpoint_label.set_text(self.dewpoint_str)
        self.feels_like_label.set_text(self.feels_like_str)
        self.humidity_label.set_text(self.humidity_str)
        self.low_temp_label.set_text(self.low_temp_str)
        self.high_temp_label.set_text(self.high_temp_str)
        if self.need_to_update_condition_desc_animation:
            self.condition_description_label.set_text(self.combined_long_desc)
            self.stage.clear_animations_for(self.condition_description_label)
            self.condition_description_label.set_position(self.condition_description_label_position)
            if self.condition_description_label.size[0] > self.stage.size[0]:
                scroll_distance = self.condition_description_label.size[0] - self.stage.size[0]
                # scroll duration: 6 seconds per full width
                scroll_duration = 6.0 * scroll_distance / self.stage.size[0]
                pause_duration = 5.0
                self.logger.debug(f"Adding scroll animation for condition text. "
                                  f"Text width: {self.condition_description_label.size[0]} px, "
                                  f"scroll distance: {scroll_distance}")

                pause_1 = Still(name='Condition-pause-1', actor=self.condition_description_label,
                                duration=pause_duration)

                scroll_left = StraightMove(name='Condition-scroll-left', actor=self.condition_description_label,
                                           duration=scroll_duration, distance=(-scroll_distance, 0),
                                           easing=Easing.LINEAR)

                pause_2 = Still(name='Condition-pause-2', actor=self.condition_description_label,
                                duration=pause_duration)

                scroll_right = StraightMove(name='Condition-scroll-right', actor=self.condition_description_label,
                                            duration=scroll_duration, distance=(scroll_distance, 0),
                                            easing=Easing.LINEAR)

                condition_sequence = Sequence(name='Condition-scroll-sequence', actor=self.condition_description_label,
                                              animations=[pause_1, scroll_left, pause_2, scroll_right],
                                              repeat=True)

                self.stage.add_animation(condition_sequence)
            else:
                self.logger.debug(f"Not adding scroll animation for condition text. "
                                  f"Text width: {self.condition_description_label.size[0]} px")
            self.need_to_update_condition_desc_animation = False

        # figure out whether it is day or night
        # time_of_day = time.strftime(timestamp_format, time.localtime())
        time_of_day = time.time()
        # self.logger.debug(f"RAW: Sunrise: {self.sunrise}, sunset: {self.sunset}, time of day: {time_of_day}")
        last_is_daytime = self.is_daytime
        self.is_daytime = self.sunrise < time_of_day < self.sunset
        if self.is_daytime != last_is_daytime:
            sunrise_str = self.format_epoch_time(self.sunrise)
            sunset_str = self.format_epoch_time(self.sunset)
            tod_str = self.format_epoch_time(time_of_day)
            if self.fresh_weather_data:
                self.logger.debug(f"Sunrise: {sunrise_str}, sunset: {sunset_str}, time of day: {tod_str}")
            if self.fresh_weather_data:
                self.logger.debug(f"Is is daytime? {self.is_daytime}")

        # sunrise or sunset are within 30 minutes of the threshold
        is_sunrise = abs(self.sunrise - time_of_day) < (30*60)
        is_sunset = abs(self.sunset - time_of_day) < (30*60)

        last_is_moon_out = self.is_moon_out
        moonrise_before_sunset = self.moonrise < self.moonset
        if moonrise_before_sunset:
            self.is_moon_out = self.moonrise < time_of_day < self.moonset
        else:
            # this is tricky
            self.is_moon_out = time_of_day < self.moonset or self.moonrise < time_of_day
        if self.is_moon_out != last_is_moon_out:
            tod_str = self.format_epoch_time(time_of_day)
            self.logger.debug(f"Moonrise: {self.format_epoch_time(self.moonrise)}, "
                              f"moonset: {self.format_epoch_time(self.moonset)}, "
                              f"time of day: {tod_str}")
            self.logger.debug(f"Is moon out? {self.is_moon_out}")

        # conditions
        # sprite names for conditions we can show
        # "sunny"  "cloudy" "rainy"  "lightning"  "snowflake-large" "snowflake-small"
        #   "foggy" "windy"

        if self.is_daytime:
            self.main_daytime_image.show()
            self.support_daytime_image_1.show()
            self.daytime_image_shadow.show()
            main_condition_sprite = None
            support_condition_sprite_1 = None
            support_condition_sprite_2 = None
            self.support_daytime_image_1.set_position(self.main_daytime_image.position)
            self.support_daytime_image_2.set_position(self.main_daytime_image.position)
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
            # reference: https://openweathermap.org/weather-conditions
            if 200 <= self.condition_code <= 299:
                main_condition_sprite = 'cloudy'
                support_condition_sprite_1 = 'rainy'
                support_condition_sprite_2 = 'lightning'
            elif 300 <= self.condition_code <= 399:
                main_condition_sprite = 'cloudy'
                support_condition_sprite_1 = 'rainy'
            elif 500 <= self.condition_code <= 599:
                main_condition_sprite = 'cloudy'
                support_condition_sprite_1 = 'rainy'
                if self.condition_code == 511:
                    support_condition_sprite_2 = 'snowflake-small'
            elif 600 <= self.condition_code <= 699:
                main_condition_sprite = 'cloudy'
                if self.condition_code in [602, 622]:
                    support_condition_sprite_1 = 'snowflake-large'
                elif 612 <= self.condition_code <= 621:
                    support_condition_sprite_1 = 'rainy'
                    support_condition_sprite_2 = 'snowflake-small'
                else:
                    support_condition_sprite_1 = 'snowflake-small'
            elif 700 <= self.condition_code <= 799:
                main_condition_sprite = 'foggy'
            elif 800 == self.condition_code:
                main_condition_sprite = 'sunny'
            elif 801 == self.condition_code:
                main_condition_sprite = 'cloudy'
                support_condition_sprite_1 = 'sunny'
            elif 802 <= self.condition_code <= 803:
                main_condition_sprite = 'sunny'
                support_condition_sprite_1 = 'cloudy'
                self.support_daytime_image_1.move((3, 5))
            elif 804 <= self.condition_code <= 899:
                main_condition_sprite = 'cloudy'
            if self.fresh_weather_data:
                self.logger.debug(f"Selected conditions sprite: {main_condition_sprite}")
            self.main_daytime_image.set_sprite(main_condition_sprite)
            self.support_daytime_image_1.set_sprite(support_condition_sprite_1)
            self.support_daytime_image_2.set_sprite(support_condition_sprite_2)
            self.daytime_image_shadow.set_sprite(main_condition_sprite)
        else:
            # is not daytime
            # if self.fresh_weather_data: self.logger.debug("Not showing daytime conditions")
            # OW interpretation
            # reference: https://openweathermap.org/weather-conditions
            support_condition_sprite_1 = None
            support_condition_sprite_2 = None
            if 200 <= self.condition_code <= 299:
                # main_condition_sprite = 'cloudy'
                support_condition_sprite_1 = 'rainy'
                support_condition_sprite_2 = 'lightning'
            elif 300 <= self.condition_code <= 399:
                support_condition_sprite_1 = 'cloudy'
                support_condition_sprite_2 = 'rainy'
            elif 500 <= self.condition_code <= 599:
                support_condition_sprite_1 = 'cloudy'
                support_condition_sprite_2 = 'rainy'
                if self.condition_code == 511:
                    support_condition_sprite_2 = 'snowflake-small'
            elif 600 <= self.condition_code <= 699:
                support_condition_sprite_1 = 'cloudy'
                if self.condition_code in [602, 622]:
                    support_condition_sprite_2 = 'snowflake-large'
                elif 612 <= self.condition_code <= 621:
                    support_condition_sprite_1 = 'rainy'
                    support_condition_sprite_2 = 'snowflake-small'
                else:
                    support_condition_sprite_2 = 'snowflake-small'
            elif 700 <= self.condition_code <= 799:
                support_condition_sprite_1 = 'foggy'
            elif 800 <= self.condition_code <= 802:
                # main_condition_sprite = 'cloudy'
                # support_condition_sprite_1 = 'sunny'
                pass
            elif 803 <= self.condition_code <= 899:
                support_condition_sprite_1 = 'cloudy'

            self.support_daytime_image_1.set_sprite(support_condition_sprite_1)
            self.support_daytime_image_2.set_sprite(support_condition_sprite_2)

            self.main_daytime_image.hide()
            self.support_daytime_image_1.show()
            self.support_daytime_image_1.show()
            self.daytime_image_shadow.hide()

        # moon phase
        if not self.is_daytime:
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
            if self.fresh_weather_data:
                self.logger.debug(f"Not showing moon phase")
            self.moon_phase_image.hide()

        # Background image

        # set background based on condition
        # OW interpretation
        self.background_image.set_from_image(None)
        if self.is_daytime:
            if 200 <= self.condition_code <= 299 or 600 <= self.condition_code <= 699:
                self.background_image.set_from_image(self.cloudy_image)
            elif 300 <= self.condition_code <= 399:
                self.background_image.set_from_image(self.cloudy_image)
            elif 500 <= self.condition_code <= 599:
                self.background_image.set_from_image(self.cloudy_image)
            elif 500 <= self.condition_code <= 599:
                self.background_image.set_from_image(self.cloudy_image)
            elif 700 <= self.condition_code <= 799:
                # smoke, haze, dist
                if self.condition_code in [711, 721, 731, 761]:
                    if is_sunrise or is_sunset:
                        self.background_image.set_from_image(self.sunrise_sunset_image)
                    else:
                        self.background_image.set_from_image(self.blue_sky_image)
                # mist, fog, sand, ash, squall, tornado!
                else:
                    self.background_image.set_from_image(self.cloudy_image)
            elif 800 <= self.condition_code <= 803:
                if is_sunrise or is_sunset:
                    self.background_image.set_from_image(self.sunrise_sunset_image)
                else:
                    self.background_image.set_from_image(self.blue_sky_image)
            elif 804 <= self.condition_code <= 899:
                self.background_image.set_from_image(self.cloudy_image)
        else:
            if 200 <= self.condition_code <= 299 or 600 <= self.condition_code <= 699:
                self.background_image.set_from_image(self.dark_clouds_image)
            elif 300 <= self.condition_code <= 399:
                self.background_image.set_from_image(self.dark_clouds_image)
            elif 500 <= self.condition_code <= 599:
                self.background_image.set_from_image(self.dark_clouds_image)
            elif 500 <= self.condition_code <= 599:
                self.background_image.set_from_image(self.dark_clouds_image)
            elif 700 <= self.condition_code <= 799:
                # smoke, haze, dust
                if self.condition_code in [711, 721, 731, 761]:
                    if is_sunrise or is_sunset:
                        self.background_image.set_from_image(self.sunrise_sunset_image)
                    else:
                        self.background_image.set_from_image(self.night_sky_image)
                # mist, fog, sand, ash, squall, tornado!
                else:
                    self.background_image.set_from_image(self.dark_clouds_image)
            elif 800 <= self.condition_code <= 803:
                if is_sunrise or is_sunset:
                    self.background_image.set_from_image(self.sunrise_sunset_image)
                else:
                    self.background_image.set_from_image(self.night_sky_image)
            elif 804 <= self.condition_code <= 899:
                self.background_image.set_from_image(self.dark_clouds_image)
        if self.background_image.image is None:
            self.logger.warning(f"Unrecognized condition code: {self.condition_code}")

        last_background_image_name = self.bg_image_name
        if self.background_image:
            if self.background_image.image == self.cloudy_image:
                self.bg_image_name = "cloudy"
            elif self.background_image.image == self.dark_clouds_image:
                self.bg_image_name = "dark_clouds"
            elif self.background_image.image == self.sunrise_sunset_image:
                self.bg_image_name = "sunrise_sunset"
            elif self.background_image.image == self.blue_sky_image:
                self.bg_image_name = "blue_sky"
            elif self.background_image.image == self.night_sky_image:
                self.bg_image_name = "night_sky"
            else:
                self.bg_image_name = "none"
        else:
            self.bg_image_name = "none"

        if last_background_image_name != self.bg_image_name:
            self.logger.debug(f"Setting background image to {self.bg_image_name}")

        # timer line, shows remaining time until next call to refresh weather data
        # old_size = self.timer_line.size
        if self.last_weather_data_at:
            time_since_last_update = time.time() - self.last_weather_data_at
            relative_length = int(round(max(round(self.refresh_time - time_since_last_update), 0) * 64.0 / self.refresh_time))
        else:
            relative_length = 0
        self.timer_line.set_start((64 - relative_length, 31))

        # if old_size[0] != self.timer_line.size[0]:
        #     self.logger.debug(f"Timer line length is now {relative_length}")

        self.timer_line.set_color((255, 255, 0, 128) if self.is_daytime else (0, 0, 255, 128))

        # set brightness according to time of day
        self.old_brightness = app_runner.matrix_options.brightness
        if self.is_daytime:
            app_runner.matrix_options.brightness = 100
        elif is_sunset or is_sunrise:
            app_runner.matrix_options.brightness = 85
        elif time_of_day < 5 * 60 * 60 or time_of_day > 22 * 60 * 60:
            app_runner.matrix_options.brightness = 60
        else:
            app_runner.matrix_options.brightness = 70

        if self.old_brightness != app_runner.matrix_options.brightness:
            self.logger.debug(f"Setting brightness to {app_runner.matrix_options.brightness}")
            self.stage.matrix.brightness = app_runner.matrix_options.brightness

        self.old_brightness = app_runner.matrix_options.brightness

        self.fresh_weather_data = False

    @staticmethod
    def get_app_instance():
        # get environment variables
        env_api_key = app_runner.get_env_parameter('OW_API_KEY', 'openweather', 'ow_api_key')
        env_latitude = app_runner.get_env_parameter('LATITUDE', 'location', 'latitude')
        env_longitude = app_runner.get_env_parameter('LONGITUDE', 'location', 'longitude')
        env_refresh_time = int(app_runner.get_env_parameter('REFRESH_TIME', 'settings', 'refresh_time',
                                                            default=60 * 15))  # default to 15 minutes

        resource_path = os.path.dirname(__file__)
        return WeatherApp(api_key=env_api_key, latitude=env_latitude, longitude=env_longitude,
                          refresh_time=env_refresh_time, resource_path=resource_path)


if __name__ == "__main__":
    app_runner.start_app(WeatherApp.get_app_instance())
