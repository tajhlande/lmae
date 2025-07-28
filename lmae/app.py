import asyncio
import logging
import time

from abc import ABCMeta, abstractmethod
from threading import Lock
from typing import Callable

from lmae.core import Stage, Actor, Animation

# hackity hackington to determine whether we're going to use virtual bindings or not
import platform
os_name = platform.system()
if os_name == 'Linux':
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
else:  # Windows or Darwin aka macOS
    from lmae.display import VirtualRGBMatrix as RGBMatrix, VirtualRGBMatrixOptions as RGBMatrixOptions


class App(metaclass=ABCMeta):
    """
    An app is a self-contained instance that knows how to compute and render itself on the LED matrix.
    Apps that want to run should extend this class or use an existing extension and implement the abstract methods.
    An initialized matrix object and matrix options are provided for rendering purposes.
    """
    def __init__(self):
        self.matrix = None
        self.matrix_options = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
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


class SingleStageRenderLoopApp(App):
    """
    Using a single stage, render within an unmanaged loop.
    This rendering will happen at the maximum possible frame rate, which defaults to 120 fps.

    This is a good candidate for an app if you want to implement callback methods to set up
    your actors and animations and specify behavior, and the view is relatively simple.
    """

    def __init__(self, size: tuple[int, int] = (64, 32), max_frame_rate: int = 120):
        """
        Initialize the app.
        :param size: Set the size of the display in pixels.
        :param max_frame_rate: Set the maximum frame rate in fps.
        """
        super().__init__()
        self.size = size
        self.lock = Lock()
        self.stage = None
        self.actors = list()
        self.animations = list()
        self.pre_render_callback = None
        self.max_frame_rate = max_frame_rate

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
        if not self.stage:
            self.stage = Stage(name=f"{self.__class__.__name__}-Stage", size=self.size,
                               matrix=self.matrix, matrix_options=self.matrix_options,
                               actors=self.actors, animations=self.animations)
        else:
            self.stage.actors = self.actors or list()
            self.stage.animations = self.animations or list()
            self.stage.blank_canvas()

    async def run(self):
        await super().run()
        self.logger.debug("Run started")
        self.running = True
        min_time_per_frame = 1.0 / self.max_frame_rate
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
                    sleep_time = min_time_per_frame - elapsed_render_time
                    # self.logger.debug(f"Sleeping for {sleep_time}")
                    await asyncio.sleep(sleep_time)

                # mark the timestamp
                last_time = time.perf_counter()
        except:
            self.logger.exception("Exception while running app")
        finally:
            self.logger.debug("Run stopped")

    def stop(self):
        self.logger.debug("Got command to stop")
        self.running = False


class DisplayManagedApp(App, metaclass=ABCMeta):
    """
    An app with a single stage, where the display refresh rate is managed to a limit,
    and rendering only happens when it is needed (when some changes to the actors on a stage
    require re-rendering).

    This is a good candidate to use if you want to override the class with your own app class.
    """

    # noinspection PyTypeChecker
    def __init__(self, refresh_time: int = 300, max_frame_rate: int = 20):
        """
        Initialize the app.

        :param refresh_time: The time between calls to `self.update_view()`, in seconds
        :param max_frame_rate: The maximum frame rate, in fps
        """
        super().__init__()
        self.refresh_time = refresh_time
        self.max_frame_rate = max_frame_rate
        self.stage: Stage = None

    def prepare(self):
        super().prepare()
        if not self.stage:
            self.stage = Stage(name=f"{self.__class__.__name__}-Stage", matrix=self.matrix,
                               matrix_options=self.matrix_options)
        else:
            self.stage.blank_canvas()

    @abstractmethod
    def update_view(self, elapsed_time: float):
        """
        Apps should use this method to update the view of the stage that will be displayed.

        This method will be called on every frame, and should
        be efficient for that reason. If the view isn't actually updating,
        it should return quickly without doing excessive work.
        :param elapsed_time: How much time has elapsed since the last time `self.update_view()` was called, in seconds
        """
        pass

    async def run(self):
        await super().run()
        self.logger.debug("Run started")
        # self.compose_view()

        min_time_per_frame = 1.0 / self.max_frame_rate
        self.logger.debug(f"Maximum frame rate: {self.max_frame_rate} fps")
        self.logger.debug(f"Minimum time per frame: {min_time_per_frame * 1000:.3f} ms")

        try:
            while self.running:
                # update the view
                self.update_view(elapsed_time=0.0)
                if self.stage.needs_render:
                    self.stage.render_frame()

                # wait 5 minutes
                waiting = True
                wait_start = time.time()
                self.logger.debug(f"Waiting {self.refresh_time / 60} minutes to refresh view")
                last_time = time.perf_counter()
                while waiting and self.running:
                    current_time = time.time()
                    elapsed_time = current_time - wait_start
                    self.update_view(elapsed_time=elapsed_time)
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
                        # must yield some control, with minimal sleep amount
                        await asyncio.sleep(min_time_per_frame/10.0)

                    # mark the timestamp
                    last_time = time.perf_counter()

        finally:
            self.logger.debug("Run stopped")
