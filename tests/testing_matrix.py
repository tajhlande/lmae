import logging
from typing import Optional
from PIL import Image

class TestingRGBMatrixOptions:
    """
    A stand-in class for rgbmatrix.RGBMatrixOptions
    Useful in testing, does not invoke Pygame
    """
    def __init__(self):
        # defaults
        self.hardware_mapping = "regular"
        self.rows = 32
        self.cols = 64
        self.chain_length = 1
        self.parallel = 1
        self.row_address_type = 0
        self.multiplexing = 0
        self.pwm_bits = 11
        self.brightness = 100
        self.pwm_lsb_nanoseconds = 130
        self.led_rgb_sequence = "RGB"
        self.pixel_mapper_config = ""
        self.panel_type = ""
        self.show_refresh_rate = 1
        self.gpio_slowdown = 1
        self.disable_hardware_pulsing = True
        self.drop_privileges = False


# noinspection PyPep8Naming
# we are mocking the method names from the rgbmatrix library
class TestingFrameCanvas:

    def __init__(self):
        self.logger = logging.getLogger("TestingFrameCanvas")
        self.image: Image = None
        self.options: Optional[TestingRGBMatrixOptions] = None
        self.offset_x = 0
        self.offset_y = 0


    def SetImage(self, image: Image, offset_x: int = 0, offset_y: int = 0):
        self.image = image
        self.offset_x = offset_x
        self.offset_y = offset_y



# noinspection PyPep8Naming,PyMethodMayBeStatic
# we are mocking the method names from the rgbmatrix library
class TestingRGBMatrix:
    """
    A stand-in class for rgbmatrix.RGBMatrix
    Useful in testing, does not invoke Pygame
    """
    def __init__(self, options: TestingRGBMatrixOptions = None):
        self.logger = logging.getLogger("TestingRGBMatrix")
        if not options:
            self.logger.error("Missing TestingRGBMatrixOptions")

        self.matrix_options: TestingRGBMatrixOptions = options
        self.frame_canvas = TestingFrameCanvas()


    def CreateFrameCanvas(self) -> TestingFrameCanvas:
        # self.logger.info("Creating frame canvas")
        frame_canvas = TestingFrameCanvas()
        return frame_canvas

    @staticmethod
    def adjust_brightness(colors: tuple[int, int, int], adjustment: float) -> tuple[int, int, int]:
        def adjust_fn(x): return max(0, min(255, 255 - int((255 - x) / adjustment)))
        new_colors = (adjust_fn(colors[0]), adjust_fn(colors[1]), adjust_fn(colors[2]))
        return new_colors

    @staticmethod
    def _get_image_pixel(image: Image, x: int, y: int) -> tuple[int, int, int]:
        if 0 <= x < image.size[0] and 0 <= y < image.size[1]:
            return image.getpixel((x, y))
        else:
            return 0, 0, 0

    def SwapOnVSync(self, frame_canvas: TestingFrameCanvas) -> TestingFrameCanvas:
        self.frame_canvas = frame_canvas
        return self.CreateFrameCanvas()
