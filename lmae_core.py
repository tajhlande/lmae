# Core classes for LED Matrix Animation Engine
import argparse
import logging
import os
import sys
import time
from abc import ABCMeta, abstractmethod
from PIL import Image, ImageDraw

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/..'))
from rgbmatrix import RGBMatrix, RGBMatrixOptions

logger = logging.getLogger("lmae_core")
logger.setLevel(logging.DEBUG)

_current_sequence = dict()


def _get_sequential_name(class_name : str = "Object"):
    if class_name not in _current_sequence:
        _current_sequence[class_name] = 0
    return f"{class_name}_{++_current_sequence[class_name]}"


class LMAEObject:
    """
    Base object for everything
    """

    def __init__(self, name: str = None):
        self.name = name or _get_sequential_name("Object")  # 'Object_' + f'{randrange(65536):04X}'
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)


class Canvas(LMAEObject):
    """
    A Canvas is an object on which other objects render themselves
    """
    def __init__(self, name: str = None, size: tuple[int, int] = (64, 32), background_fill: bool = True):
        name = name or _get_sequential_name("Canvas")  # 'Canvas_' + f'{randrange(65536):04X}'
        super().__init__(name=name)
        self.size = size
        self.image = Image.new("RGBA", self.size, (0, 0, 0, 255 if background_fill else 0))
        self.image_draw = ImageDraw.Draw(self.image)

    def blank(self):
        draw = ImageDraw.Draw(self.image)
        draw.rectangle(((0, 0), (self.size[0] - 1, self.size[1] - 1)), fill='black', width=0)


class Actor(LMAEObject):
    """
    An object that appears on a stage and knows how to render itself
    """
    def __init__(self, name: str = None, position: tuple[int, int] = (0, 0)):
        name = name or _get_sequential_name("Actor")  # 'Actor_' + f'{randrange(65536):04X}'
        super().__init__(name=name)
        self.position = position
        self.size = 0, 0
        self.changes_since_last_render = True  # since we've not been rendered yet
        self.visible = True

    def set_position(self, position: tuple[int, int]):
        if not (position == self.position):
            self.position = position
            self.changes_since_last_render = True

    def set_visible(self, visible: bool):
        if self.visible != visible:
            self.visible = visible
            self.changes_since_last_render = True

    def show(self):
        self.set_visible(True)

    def hide(self):
        self.set_visible(False)

    def update(self):
        pass

    def render(self, canvas: Canvas):
        self.changes_since_last_render = False
        pass


class Animation(LMAEObject, metaclass=ABCMeta):
    """
    A clock-based way to update an actor based on elapsed real time.
    This base class should be extended to provide specific animation behaviors.
    """

    def __init__(self, name: str = None, actor: Actor = None, repeat: bool = False, duration: float = 1.0):
        name = name or _get_sequential_name("Animation")
        super().__init__(name=name)
        self.actor = actor
        self.repeat: bool = repeat
        self.duration = duration
        self.started = False
        self.start_time: float = 0.0
        self.last_update_time: float = 0.0
        self.end_time: float = 0.0

    def reset(self):
        self.started = False
        self.start_time = 0.0
        self.last_update_time = 0.0
        self.end_time = 0.0

    def start(self, current_time: float):
        self.logger.debug(f"Starting at {current_time}")
        self.started = True
        self.start_time = current_time

    def is_started(self):
        return self.started

    def should_repeat(self):
        return self.repeat

    def get_elapsed_time(self, current_time: float) -> float:
        if not self.started:
            return 0.0
        return current_time - self.start_time

    def get_simulated_time(self):
        if not self.started:
            return 0
        if self.last_update_time == 0:
            return 0
        return self.last_update_time - self.start_time

    def set_update_time(self, update_time):
        self.last_update_time = update_time

    @abstractmethod
    def is_finished(self) -> bool:
        """
        Override this to indicate when an animation is done.
        This should usually be based on the current time in the last call to `update_actor(current_time)`
        :return: `True` if this animation is finished, `False` otherwise
        """
        pass

    @abstractmethod
    def update_actor(self, current_time: float):
        """
        Override this to update this animation's actor based on the current time.

        Implementors must call `this.set_updated_time(time)`, usually at the end of their implementation.

        Actors must correctly reflect their state of needing to be rendered after being updated.
        If updating would cause any changes in the way an actor is rendered, then
        `actor.changes_since_last_render` must be `True`. If updating did not cause any changes in the way
        an actor is rendered, then `actor.changes_since_last_render` must be unchanged.

        :param current_time: the current time that this frame is being rendered
        """
        self.last_update_time = current_time


def _retain_animation(anim: Animation) -> bool:
    """
    Determine whether this animation should be kept in the list or not,
    based on ... is it done?  should it repeat?
    :param anim: the animation
    :return: `True` if we retain it, `False` otherwise
    """
    # logger.debug(f"Retain animation {anim.name}? finished: {anim.is_finished()}, repeat: {anim.should_repeat()}")
    if anim.is_finished() and anim.should_repeat():
        anim.reset()
    return not anim.is_finished() or anim.should_repeat()


class Stage(LMAEObject):
    """
    An environment with a set of actors who appear in a certain order, all of whom can
    render themselves onto a canvas on demand.  The canvas can then be displayed on the
    LED matrix.

    Rendering to the canvas is double-buffered, to avoid seeing intermediate renders on
    the LED matrix.
    """
    def __init__(self, name=None, size: tuple[int, int] = (64, 32), actors: list[Actor] = None,
                 animations: list[Animation] = None,
                 matrix: RGBMatrix = None,
                 matrix_options: RGBMatrixOptions = None):
        name = name or _get_sequential_name("Stage")  # 'Stage_' + f'{randrange(65536):04X}'
        super().__init__(name)
        self.size = size        # size in pixels
        self.actors = actors or list()
        self.animations = animations or list()
        self.canvas = Canvas(size=self.size)
        self.matrix = matrix or (RGBMatrix(options=matrix_options) if matrix_options else None)
        if not self.matrix:
            self.logger.warning("No matrix or matrix options were provided to the stage")
        self.double_buffer = self.matrix.CreateFrameCanvas()
        self.needs_render = True

    def add_animation(self, animation: Animation):
        """
        Add an animation to this stage
        :param animation: the animation to add
        """
        self.animations.append(animation)

    def prepare_frame(self):
        """
        Prepare for a frame to be rendered
        :return:
        """
        self.canvas.blank()

    def update_actors(self):
        """
        Let all the actors update themselves, including applying animations
        """
        current_time = time.perf_counter()
        # self.logger.debug(f"Current time: {current_time}")

        # run all the animations
        for anim in self.animations:
            self.logger.debug(f"Running animation {anim.name}")
            # see if we need to start them
            if not anim.is_started():
                self.logger.debug(f"Animation {anim.name} is starting")
                anim.start(current_time)

            # update each animation
            anim.update_actor(current_time)
            anim.last_render_time = current_time

        # update the actors
        # self.logger.debug("Updating actors")
        self.needs_render = False
        for actor in self.actors:
            actor.update()
            self.needs_render = self.needs_render or actor.changes_since_last_render
            # self.logger.debug(f"Needs render after {actor.name}: {self.needs_render}")

    def render_actors(self):
        """
        Draw all the actors in the frame
        :return:
        """
        for actor in self.actors:
            if actor.visible:
                actor.render(self.canvas)
            actor.changes_since_last_render = False

    def post_render(self):
        """
        Perform post-render activities.
        """
        # clean up finished animations
        self.animations = [anim for anim in self.animations if _retain_animation(anim)]
        # self.logger.debug(f"After post-render, animations list is now {len(self.animations)} long")

    def display_frame(self):
        """
        Swap out the rendered frame on a vertical sync
        :return:
        """
        self.double_buffer.SetImage(self.canvas.image.convert("RGB"), 0, 0)
        self.double_buffer = self.matrix.SwapOnVSync(self.double_buffer)

    def render_frame(self):
        """
        Do all steps to render and display a frame update
        :return:
        """
        # self.logger.debug("Rendering the frame")
        self.update_actors()
        if self.needs_render:
            # self.logger.debug("Render update needed")
            self.prepare_frame()
            self.render_actors()
            self.display_frame()
        else:
            # self.logger.debug("Render update not needed")
            pass  # no update needed
        self.post_render()


def parse_matrix_options_command_line():
    """
    Parse the command line options and construct a RGBMatrixOptions object
    :return: an RGBMatrixOptions object
    """
    options = RGBMatrixOptions()
    parser = argparse.ArgumentParser()

    parser.add_argument("-r", "--led-rows", action="store",
                        help="Display rows. 16 for 16x32, 32 for 32x32. Default: 32", default=32, type=int)
    parser.add_argument("--led-cols", action="store",
                        help="Panel columns. Typically 32 or 64. (Default: 64)", default=64, type=int)
    parser.add_argument("-c", "--led-chain", action="store",
                        help="Daisy-chained boards. Default: 1.", default=1, type=int)
    parser.add_argument("-P", "--led-parallel", action="store",
                        help="For Plus-models or RPi2: parallel chains. 1..3. Default: 1", default=1, type=int)
    parser.add_argument("-p", "--led-pwm-bits", action="store",
                        help="Bits used for PWM. Something between 1..11. Default: 11", default=11, type=int)
    parser.add_argument("-b", "--led-brightness", action="store",
                        help="Sets brightness level. Default: 100. Range: 1..100", default=100, type=int)
    parser.add_argument("-m", "--led-gpio-mapping",
                        help="Hardware Mapping: regular, adafruit-hat, adafruit-hat-pwm",
                        choices=['regular', 'regular-pi1', 'adafruit-hat', 'adafruit-hat-pwm'], type=str)
    parser.add_argument("--led-scan-mode", action="store",
                        help="Progressive or interlaced scan. 0 Progressive,  1 Interlaced (default)",
                        default=1, choices=range(2), type=int)
    parser.add_argument("--led-pwm-lsb-nanoseconds", action="store",
                        help="Base time-unit for the on-time in the lowest significant bit in nanoseconds. "
                             "Default: 130",  default=130, type=int)
    parser.add_argument("--led-show-refresh", action="store_true",
                        help="Shows the current refresh rate of the LED panel")
    parser.add_argument("--led-slowdown-gpio", action="store",
                        help="Slow down writing to GPIO. Range: 0..4. Default: 1", default=1, type=int)
    parser.add_argument("--led-no-hardware-pulse", action="store",
                        help="Don't use hardware pin-pulse generation")
    parser.add_argument("--led-rgb-sequence", action="store",
                        help="Switch if your matrix has led colors swapped. Default: RGB", default="RGB", type=str)
    parser.add_argument("--led-pixel-mapper", action="store",
                        help="Apply pixel mappers. e.g \"Rotate:90\"", default="", type=str)
    parser.add_argument("--led-row-addr-type", action="store",
                        help="0 = default; 1=AB-addressed panels; 2=row direct; 3=ABC-addressed panels; "
                             "4 = ABC Shift + DE direct", default=0, type=int, choices=[0, 1, 2, 3, 4])
    parser.add_argument("--led-multiplexing", action="store",
                        help="Multiplexing type: 0=direct; 1=strip; 2=checker; 3=spiral; 4=ZStripe; "
                             "5=ZnMirrorZStripe; 6=coreman; 7=Kaler2Scan; 8=ZStripeUneven... (Default: 0)",
                        default=0, type=int)
    parser.add_argument("--led-panel-type", action="store",
                        help="Needed to initialize special panels. Supported: 'FM6126A'", default="", type=str)
    parser.add_argument("--led-no-drop-privs", dest="drop_privileges",
                        help="Don't drop privileges from 'root' after initializing the hardware.", action='store_false')
    parser.set_defaults(drop_privileges=True)

    args = parser.parse_args()

    if args.led_gpio_mapping is not None:
        options.hardware_mapping = args.led_gpio_mapping
    options.rows = args.led_rows
    options.cols = args.led_cols
    options.chain_length = args.led_chain
    options.parallel = args.led_parallel
    options.row_address_type = args.led_row_addr_type
    options.multiplexing = args.led_multiplexing
    options.pwm_bits = args.led_pwm_bits
    options.brightness = args.led_brightness
    options.pwm_lsb_nanoseconds = args.led_pwm_lsb_nanoseconds
    options.led_rgb_sequence = args.led_rgb_sequence
    options.pixel_mapper_config = args.led_pixel_mapper
    options.panel_type = args.led_panel_type

    if args.led_show_refresh:
        options.show_refresh_rate = 1
    if args.led_slowdown_gpio is not None:
        options.gpio_slowdown = args.led_slowdown_gpio
    if args.led_no_hardware_pulse:
        options.disable_hardware_pulsing = True
    if not args.drop_privileges:
        options.drop_privileges = False

    logger.debug(f"Matrix configuration:")
    logger.debug(f"    hardware_mapping:  {options.hardware_mapping}")
    logger.debug(f"    rows:  {options.rows}")
    logger.debug(f"    cols:  {options.cols}")
    logger.debug(f"    chain_length:  {options.chain_length}")
    logger.debug(f"    parallel:  {options.parallel}")
    logger.debug(f"    row_address_type:  {options.row_address_type}")
    logger.debug(f"    multiplexing:  {options.multiplexing}")
    logger.debug(f"    pwm_bits:  {options.pwm_bits}")
    logger.debug(f"    brightness:  {options.brightness}")
    logger.debug(f"    pwm_lsb_nanoseconds:  {options.pwm_lsb_nanoseconds}")
    logger.debug(f"    led_rgb_sequence:  {options.led_rgb_sequence}")
    logger.debug(f"    pixel_mapper_config:  {options.pixel_mapper_config}")
    logger.debug(f"    panel_type:  {options.panel_type}")
    logger.debug(f"    show_refresh_rate:  {options.show_refresh_rate}")
    logger.debug(f"    gpio_slowdown:  {options.gpio_slowdown}")
    logger.debug(f"    disable_hardware_pulsing:  {options.disable_hardware_pulsing}")
    logger.debug(f"    drop_privileges:  {options.drop_privileges}")

    return options
