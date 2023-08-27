import asyncio
import time
from abc import ABCMeta, abstractmethod
from lmae_core import Stage, Actor, Animation
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import logging
from threading import Lock
from typing import Callable


class AppModule(metaclass=ABCMeta):
    """
    An app module is a self-contained app that renders itself on the LED matrix.
    Apps that want to run should extend this class and implement the abstract methods.
    An initialized matrix object and matrix options are provided for rendering purposes.
    """
    def __init__(self):
        self.matrix = None
        self.matrix_options = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.running = False

    def set_matrix(self, matrix: RGBMatrix, options: RGBMatrixOptions):
        """
        Called to set the matrix object. Must be called before any abstract methods are called.
        :return:
        """
        self.logger.debug("Set matrix in app")
        self.matrix = matrix
        self.matrix_options = options

    def prepare(self):
        """
        Apps can implement this method to prepare themselves before rendering.
        :return: True if the method was successful, False if not (or throw an exception)
        """
        pass

    @abstractmethod
    async def run(self):
        """
        This method will be invoked in a distinct thread when the app should start running.
        It should be async friendly and should yield on reasonable occasion.
        It should occasionally check for `self.running`'s value, and when that value is no longer
        true, it should exit.
        :return:
        """
        self.logger.debug("Got command to start running")
        self.running = True

    def stop(self):
        """
        Apps should stop running when this method is called.
        :return:
        """
        self.logger.debug("Got command to stop")
        self.running = False


class SingleStageRenderLoopAppModule(AppModule):
    """
    Using a single stage, render a loop of items
    """

    def __init__(self):
        super().__init__()
        self.lock = Lock()
        self.stage = None
        self.actors = list()
        self.animations = list()
        self.pre_render_callback = None

    def add_actors(self, *args: Actor):
        self.actors.extend(args)

    def add_animations(self, *args: Animation):
        self.animations.extend(args)

    def set_pre_render_callback(self, pre_render_callback: Callable):
        """
        Set a function to be called before each render frame. This can be used to
        update actors. It should be fast!
        :param pre_render_callback: Reference to a function with no arguments
        """
        self.pre_render_callback = pre_render_callback

    def prepare(self):
        self.stage = Stage(matrix=self.matrix, matrix_options=self.matrix_options,
                           actors=self.actors, animations=self.animations)

    async def run(self):
        await super().run()
        self.logger.debug("Run started")
        self.running = True
        max_frame_rate = 120
        min_time_per_frame = 1.0 / max_frame_rate
        i = 0
        last_time = time.perf_counter()
        try:
            while self.running:
                # call pre-render callback
                if self.pre_render_callback:
                    self.pre_render_callback()

                # render the frame
                self.stage.render_frame()

                # calculate the frame rate and render that
                render_end_time = time.perf_counter()

                # if we are rendering faster than max frame rate, slow down
                elapsed_render_time = render_end_time - last_time
                if elapsed_render_time < min_time_per_frame:
                    await asyncio.sleep(min_time_per_frame - elapsed_render_time)

                # mark the timestamp
                last_time = time.perf_counter()
        finally:
            self.logger.debug("Run stopped")

    def stop(self):
        self.logger.debug("Got command to stop")
        self.running = False
