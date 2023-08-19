from lmae_module import AppModule
import time
from threading import Lock
from vx_wx.vx_client import get_current_conditions_by_zipcode
from lmae_core import Stage, Text, Rectangle
from PIL import ImageFont


class WeatherApp(AppModule):
    """
    Display the current weather
    """

    def __init__(self, api_key: str, zipcode: str):
        super().__init__()
        self.api_key = api_key
        self.zipcode = zipcode
        self.logger.info(f"Checking weather for ZIP code {self.zipcode}")
        self.running = False
        self.lock = Lock()
        self.stage = None
        self.actors = list()
        self.pre_render_callback = None
        self.current_conditions = None
        self.call_status = "ok"
        self.temperature_font = ImageFont.truetype("fonts/press-start-2p-font/PressStart2P-vaV7.ttf", 8)
        self.temperature_label = None
        self.timer_line = None

    # noinspection PyBroadException
    def get_current_conditions(self):
        try:
            self.logger.debug(f"Fetching current conditions for ZIP code {self.zipcode}")
            current_conditions = get_current_conditions_by_zipcode(self.zipcode, self.api_key)
            if current_conditions:
                self.logger.debug("Call to get conditions succeeded")
                self.current_conditions = current_conditions
                self.call_status = "ok"
            else:
                self.logger.error("Call to get conditions did not return any conditions")
                self.call_status = "error"
                # old conditions remain available

        except:
            self.logger.error("Call to get weather status failed")

    def compose_view(self):
        self.stage = Stage(matrix=self.matrix, matrix_options=self.matrix_options)
        self.temperature_label = Text(name='temperature', position=(5, 5), font=self.temperature_font,
                                      color=(255, 255, 255, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)
        self.timer_line = Rectangle(name='timer-line', position=(0, 31), size=(64, 1),
                                    color=(255, 0, 0), outline_color=(255, 0, 0), outline_width=0)
        self.stage.actors.append(self.temperature_label)
        self.stage.actors.append(self.timer_line)

    def update_view(self, elapsed_time: float):
        temperature = f"{round(self.current_conditions['currentConditions']['temp'])}º"
        # self.logger.debug(f"Current temperature: {temperature}")
        self.temperature_label.text = str(temperature)
        self.timer_line.size = int(round(max(round((15*60) - elapsed_time), 0) * 64 / (15*60))), 1
        self.log.debug(f"Timer line size is now {self.timer_line.size}")

    def prepare(self):
        self.compose_view()

    def run(self):
        self.logger.debug("Run started")
        self.running = True
        self.compose_view()

        try:
            while self.running:
                # get updated weather conditions
                self.get_current_conditions()

                # update the view
                self.update_view(0)
                self.stage.render_frame(1)    # frame numbers don't matter here

                # wait 15 minutes
                waiting = True
                wait_start = time.time()
                self.logger.debug("Waiting 15 minutes to refresh weather data")
                while waiting and self.running:
                    time.sleep(1)
                    current_time = time.time()
                    elapsed_time = current_time - wait_start
                    self.update_view(elapsed_time)
                    waiting = elapsed_time < (15 * 60)

        finally:
            self.logger.debug("Run stopped")

    def stop(self):
        self.logger.debug("Got command to stop")
        self.running = False
