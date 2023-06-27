# Core classes for LED Matrix Animation Engine
import argparse
import logging
from random import randrange
from PIL import Image, ImageDraw, ImageFont

from rgbmatrix import RGBMatrix, RGBMatrixOptions

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


class Canvas(LMAEObject):
    """
    A Canvas is an object on which other objects render themselves
    """
    def __init__(self, name: str = None, size: tuple[int, int] = (64, 32)):
        name = name or _get_sequential_name("Canvas")  # 'Canvas_' + f'{randrange(65536):04X}'
        super().__init__(name=name)
        self.size = size
        self.image = Image.new("RGBA", self.size, (0, 0, 0))
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
        self.changes_since_last_render = True # since we've not been rendered yet

    def update(self):
        pass

    def render(self, canvas: Canvas):
        self.changes_since_last_render = False


class StillImage(Actor):
    """
    An unchanging image that can position itself on a stage
    """
    def __init__(self, name: str = None, position: tuple[int, int] = (0, 0), image: Image = None):
        name = name or _get_sequential_name("StillImage")  # 'StillImage_' + f'{randrange(65536):04X}'
        super().__init__(name=name, position=position)
        self.image = image
        self.size = self.image.size if self.image else (0, 0)

    def set_from_file(self, filename):
        self.image = Image.open(filename)
        if not self.image.mode == 'RGBA':
            self.image = self.image.convert('RGBA')
        self.size = self.image.size

    def render(self, canvas: Canvas):
        super().render(canvas)
        if self.image:
            canvas.image.alpha_composite(self.image, dest=self.position)


class Text(Actor):
    """
    Text that renders on a stage
    """

    def __init__(self,
                 font: ImageFont,
                 name: str = None,
                 position: tuple[int, int] = (0, 0),
                 text: str = None,
                 color: tuple[int, int, int] = (255, 255, 255, 255),
                 stroke_color: tuple[int, int, int] = (0, 0, 0, 255),
                 stroke_width: int = 0):
        name = name or _get_sequential_name("Text")  # 'Text_' + f'{randrange(65536):04X}'
        super().__init__(name=name, position=position)
        self.font = font
        self.text = text
        self.color = color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width

    def render(self, canvas: Canvas):
        super().render(canvas)
        if self.text:
            image = Image.new("RGBA", self.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            logging.debug(f"Drawing text at {self.position} with color {self.color}, font {self.font.getname()}, "
                          f"stroke_fill {self.stroke_color} and stroke_width {self.stroke_width}: '{self.text}'")
            draw.text(self.position, self.text, fill=self.color, font=self.font,
                      stroke_fill=self.stroke_color, stroke_width=self.stroke_width)


class Stage(LMAEObject):
    """
    An environment with a set of actors who appear in a certain order, all of whom can
    render themselves onto a canvas on demand.  The canvas can then be displayed on the
    LED matrix.

    Rendering to the canvas is double-buffered, to avoid seeing intermediate renders on
    the LED matrix.
    """
    def __init__(self, name=None, size: tuple[int, int] = (64, 32), actors: list = None, matrix: RGBMatrix = None,
                 matrix_options: RGBMatrixOptions = None):
        name = name or _get_sequential_name("Stage")  # 'Stage_' + f'{randrange(65536):04X}'
        super().__init__(name)
        self.size = size        # size in pixels
        self.actors = actors or list()
        self.canvas = Canvas(size=self.size)
        self.matrix = matrix or RGBMatrix(options=matrix_options)
        self.double_buffer = self.matrix.CreateFrameCanvas()

    def prepare_frame(self):
        """
        Prepare for a frame to be rendered
        :return:
        """
        self.canvas.blank()

    def update_actors(self):
        """
        Let all the actors update themselves
        :return:
        """
        for actor in self.actors:
            actor.update()

    def render_actors(self):
        """
        Draw all the actors in the frame
        :return:
        """
        for actor in self.actors:
            actor.render(self.canvas)

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
        self.update_actors()
        self.prepare_frame()
        self.render_actors()
        self.display_frame()


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

    logging.debug(f"Matrix configuration:")
    logging.debug(f"    hardware_mapping:  {options.hardware_mapping}")
    logging.debug(f"    rows:  {options.rows}")
    logging.debug(f"    cols:  {options.cols}")
    logging.debug(f"    chain_length:  {options.chain_length}")
    logging.debug(f"    parallel:  {options.parallel}")
    logging.debug(f"    row_address_type:  {options.row_address_type}")
    logging.debug(f"    multiplexing:  {options.multiplexing}")
    logging.debug(f"    pwm_bits:  {options.pwm_bits}")
    logging.debug(f"    brightness:  {options.brightness}")
    logging.debug(f"    pwm_lsb_nanoseconds:  {options.pwm_lsb_nanoseconds}")
    logging.debug(f"    led_rgb_sequence:  {options.led_rgb_sequence}")
    logging.debug(f"    pixel_mapper_config:  {options.pixel_mapper_config}")
    logging.debug(f"    panel_type:  {options.panel_type}")
    logging.debug(f"    show_refresh_rate:  {options.show_refresh_rate}")
    logging.debug(f"    gpio_slowdown:  {options.gpio_slowdown}")
    logging.debug(f"    disable_hardware_pulsing:  {options.disable_hardware_pulsing}")
    logging.debug(f"    drop_privileges:  {options.drop_privileges}")

    return options
