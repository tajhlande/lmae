import asyncio
import datetime
import time

from datetime import datetime
from PIL import ImageFont

import app_runner
from lmae.core import Stage
from lmae.app import App
from lmae.actor import StillImage


class WorldClock(App):
    """
    Display a projection of the world with a day-night separator.
    """

    # noinspection PyTypeChecker
    def __init__(self, refresh_time: int = 300):
        super().__init__()
        self.stage: Stage = None
        self.actors = list()
        self.pre_render_callback = None
        self.refresh_time = refresh_time
        self.big_font = ImageFont.truetype("fonts/Roboto/Roboto-Light.ttf", 15)
        self.daytime_map = StillImage(name="daytime-map")
        self.daytime_map.set_from_file("images/visible-earth/world-topo-bathy.png")
        self.nighttime_map = StillImage(name="nighttime-map")
        self.nighttime_map.set_from_file("images/visible-earth/black-marble.png")
        self.current_datetime = None

    def compose_view(self):
        self.stage = Stage(matrix=self.matrix, matrix_options=self.matrix_options)
        self.stage.actors.extend((self.daytime_map, self.nighttime_map))

    def update_clock(self):
        self.current_datetime = datetime.now()

    @staticmethod
    def format_epoch_time(timestamp):
        timestamp_format = "%H:%M:%S"
        if timestamp is str:
            timestamp = float(timestamp)
        return time.strftime(timestamp_format, time.localtime(timestamp))

    def update_view(self):
        # determine counter and text label values
        self.daytime_map.hide()
        self.nighttime_map.show()

    def prepare(self):
        self.compose_view()

    async def run(self):
        await super().run()
        self.logger.debug("Run started")
        # self.compose_view()
        max_frame_rate = 20
        min_time_per_frame = 1.0 / max_frame_rate

        try:
            while self.running:
                # get updated day count
                self.update_clock()

                # update the view
                self.update_view()
                if self.stage.needs_render:
                    self.stage.render_frame()

                # wait 5 minutes
                waiting = True
                wait_start = time.time()
                self.logger.debug(f"Waiting {self.refresh_time / 60} minutes to refresh day count")
                last_time = time.perf_counter()
                while waiting and self.running:
                    current_time = time.time()
                    elapsed_time = current_time - wait_start
                    self.update_view()
                    # self.stage.needs_render = True  # have to force this for some reason
                    self.stage.render_frame()
                    waiting = elapsed_time < self.refresh_time

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


if __name__ == "__main__":
    # get environment variables
    app_runner.app_setup()
    world_clock = WorldClock()
    world_clock.set_matrix(app_runner.matrix, options=app_runner.matrix_options)
    app_runner.start_app(world_clock)
