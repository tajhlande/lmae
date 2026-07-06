import asyncio
import logging
import platform
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from threading import Lock
from typing import Self, cast

from lmae.core import Actor, Animation, Stage

os_name = platform.system()
if os_name == "Linux":
    from rgbmatrix import RGBMatrix, RGBMatrixOptions  # type: ignore
else:  # Windows or Darwin aka macOS
    from lmae.display import VirtualRGBMatrix as RGBMatrix
    from lmae.display import VirtualRGBMatrixOptions as RGBMatrixOptions


class App(ABC):
    """
    An app is a self-contained instance that knows how to compute and render
    itself on the LED matrix. Apps that want to run should extend this class
    or use an existing extension and implement the abstract methods.
    An initialized matrix object and matrix options are provided for rendering.
    """

    def __init__(self) -> None:
        self.matrix = None
        self.matrix_options = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        self.running = False

    def set_matrix(self, matrix: RGBMatrix, options: RGBMatrixOptions) -> None:
        """
        Called to set the matrix object. Must be called before any abstract methods are called.
        :return:
        """
        self.logger.debug("Set matrix in app")
        self.matrix = matrix
        self.matrix_options = options

    def prepare(self) -> None:  # noqa: B027
        """
        Apps can implement this method to prepare themselves before rendering.
        """

    @abstractmethod
    async def run(self) -> None:
        """
        This method will be invoked in a distinct thread when the app should start running.
        It should be async friendly and should yield on reasonable occasion.
        """
        self.logger.debug("Got command to start running")
        self.running = True

    def stop(self) -> None:
        self.logger.debug("Got command to stop")
        self.running = False

    @classmethod
    @abstractmethod
    def get_app_instance(cls, **kwargs: object) -> Self:
        """
        This static method should return an instance of the app with default values.
        This may, if desired, be a singleton instance.
        :return: an instance of this class
        """
        pass


class SingleStageRenderLoopApp(App):
    """
    Using a single stage, render within an unmanaged loop.
    This rendering will happen at the maximum possible frame rate, which defaults to 120 fps.

    This is a good candidate for an app if you want to implement callback methods to set up
    your actors and animations and specify behavior, and the view is relatively simple.
    """

    def __init__(self, size: tuple[int, int] = (64, 32), max_frame_rate: int = 120) -> None:
        """
        Initialize the app.
        :param size: Set the size of the display in pixels.
        :param max_frame_rate: Set the maximum frame rate in fps.
        """
        super().__init__()
        self.size = size
        self.lock = Lock()
        self.stage = None
        self.actors = []
        self.animations = []
        self.pre_render_callback = None
        self.max_frame_rate = max_frame_rate

    def add_actors(self, *args: Actor) -> None:
        self.actors.extend(args)

    def add_animations(self, *args: Animation) -> None:
        self.animations.extend(args)

    def set_pre_render_callback(self, pre_render_callback: Callable[[], None]) -> None:
        """
        Set a function to be called before each render frame. This can be used to
        update actors. It should be fast!
        :param pre_render_callback: Reference to a function with no arguments
        """
        self.pre_render_callback = pre_render_callback

    def prepare(self) -> None:
        if not self.stage:
            self.stage = Stage(
                name=f"{self.__class__.__name__}-Stage",
                size=self.size,
                matrix=self.matrix,
                matrix_options=self.matrix_options,
                actors=self.actors,
                animations=self.animations,
            )
        else:
            self.stage.actors = self.actors or []
            self.stage.animations = self.animations or []
            self.stage.blank_canvas()

    async def run(self) -> None:
        await super().run()
        self.logger.debug("Run started")
        self.running = True
        min_time_per_frame = 1.0 / self.max_frame_rate
        last_time = time.perf_counter()
        try:
            while self.running:
                if self.pre_render_callback:
                    self.pre_render_callback()

                stage = cast(Stage, self.stage)
                stage.render_frame()

                render_end_time = time.perf_counter()
                elapsed_render_time = render_end_time - last_time
                if elapsed_render_time < min_time_per_frame:
                    sleep_time = min_time_per_frame - elapsed_render_time
                    await asyncio.sleep(sleep_time)

                last_time = time.perf_counter()
        except Exception:
            self.logger.exception("Exception while running app")
        finally:
            self.logger.debug("Run stopped")

    def stop(self) -> None:
        self.logger.debug("Got command to stop")
        self.running = False

    @classmethod
    def get_app_instance(cls, **kwargs: object) -> Self:
        """
        This static method should return an instance of the app with default values.
        This may, if desired, be a singleton instance.
        :return: an instance of this class
        """
        return cast(Self, SingleStageRenderLoopApp())


class DisplayManagedApp(App, ABC):
    """
    An app with a single stage, where the display refresh rate is managed to a limit,
    and rendering only happens when it is needed (when some changes to the actors on a stage
    require re-rendering).

    This is a good candidate to use if you want to override the class with your own app class.
    """

    def __init__(self, refresh_time: int = 300, max_frame_rate: int = 20) -> None:
        """
        Initialize the app.

        :param refresh_time: The time between calls to `self.update_view()`, in seconds
        :param max_frame_rate: The maximum frame rate, in fps
        """
        super().__init__()
        self.refresh_time = refresh_time
        self.max_frame_rate = max_frame_rate
        self.stage: Stage | None = None

    def prepare(self) -> None:
        super().prepare()
        if not self.stage:
            self.stage = Stage(
                name=f"{self.__class__.__name__}-Stage",
                matrix=self.matrix,
                matrix_options=self.matrix_options,
            )
        else:
            self.stage.blank_canvas()

    @abstractmethod
    def update_view(self, elapsed_time: float) -> None:
        """
        Apps should use this method to update the view of the stage that will be displayed.

        This method will be called on every frame, and should
        be efficient for that reason. If the view isn't actually updating,
        it should return quickly without doing excessive work.
        :param elapsed_time: How much time has elapsed since the last time
            `self.update_view()` was called, in seconds
        """
        pass

    async def run(self) -> None:
        await super().run()
        self.logger.debug("Run started")

        # mark stage as needing rendering in case we've been run before
        stage = cast(Stage, self.stage)
        stage.needs_render = True

        min_time_per_frame = 1.0 / self.max_frame_rate
        self.logger.debug(f"Maximum frame rate: {self.max_frame_rate} fps")
        self.logger.debug(f"Minimum time per frame: {min_time_per_frame * 1000:.3f} ms")

        try:
            while self.running:
                # update the view
                self.update_view(elapsed_time=0.0)
                if stage.needs_render:
                    stage.render_frame()

                # wait 5 minutes
                waiting = True
                wait_start = time.time()
                self.logger.debug(f"Waiting {self.refresh_time / 60} minutes to refresh view")
                last_time = time.perf_counter()
                while waiting and self.running:
                    current_time = time.time()
                    elapsed_time = current_time - wait_start
                    self.update_view(elapsed_time=elapsed_time)
                    stage.render_frame()
                    waiting = elapsed_time < self.refresh_time

                    # calculate the frame rate and render that
                    render_end_time = time.perf_counter()

                    # if we are rendering faster than max frame rate, slow down
                    elapsed_render_time = render_end_time - last_time
                    if elapsed_render_time < min_time_per_frame:
                        sleep_time = min_time_per_frame - elapsed_render_time
                        await asyncio.sleep(sleep_time)
                    else:
                        # must yield some control, with minimal sleep amount
                        await asyncio.sleep(min_time_per_frame / 10.0)

                    # see if we're still running
                    if not self.running:
                        self.logger.debug("No longer running, breaking out of wait loop")

                    # mark the timestamp
                    last_time = time.perf_counter()

        finally:
            self.logger.debug("Run stopped")
