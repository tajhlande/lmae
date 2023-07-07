import time
from abc import ABCMeta, abstractmethod
from lmae_core import Stage
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import logging
from threading import Lock


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

    def set_matrix(self, matrix: RGBMatrix, options: RGBMatrixOptions):
        """
        Called to set the matrix object. Must be called before any abstract methods are called.
        :return:
        """
        self.logger.debug("Set matrix in app")
        self.matrix = matrix
        self.matrix_options = options

    @abstractmethod
    def prepare(self):
        """
        Apps can implement this method to prepare themselves before rendering.
        :return: True if the method was successful, False if not (or throw an exception)
        """
        pass

    @abstractmethod
    def run(self):
        """
        This method will be invoked in a distinct thread when the app should start running
        :return:
        """
        pass

    @abstractmethod
    def stop(self):
        """
        Apps should stop running when this method is called.
        :return:
        """
        pass


class SingleStageRenderLoopAppModule(AppModule):
    """
    Using a single stage, render a loop of items
    """

    def __init__(self):
        super().__init__()
        self.stage = Stage()
        self.running = False
        self.lock = Lock()

    def add_actors(self, *args):
        self.stage.actors.extend(args)

    def prepare(self):
        pass

    def run(self):
        self.logger.debug("Run started")
        self.running = True
        max_frame_rate = 120
        min_time_per_frame = 1.0 / max_frame_rate
        i = 0
        last_time = time.time()
        try:
            while self.running:
                # render the frame
                self.stage.render_frame(i)
                i += 1

                # calculate the frame rate and render that
                render_end_time = time.time()

                # if we are rendering faster than max frame rate, slow down
                elapsed_render_time = render_end_time - last_time
                if elapsed_render_time < min_time_per_frame:
                    time.sleep(min_time_per_frame - elapsed_render_time)

                # mark the timestamp
                last_time = time.time()
        finally:
            self.logger.debug("Run stopped")

    def stop(self):
        self.logger.debug("Got command to stop")
        self.running = False


