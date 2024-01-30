import logging
import pygame

from enum import auto, Enum
from PIL import Image
from typing import Optional


class PixelShape(Enum):
    ROUND = auto()
    SQUARE = auto()
    ROUND_RECT = auto()


class VirtualRGBMatrixOptions:
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


class WindowSpecs:

    def __init__(self, matrix_options: Optional[VirtualRGBMatrixOptions]):
        self.matrix_options = matrix_options
        # make sure pixel size is odd, else circle drawing of LEDs will be off
        self.led_pixel_size = 11
        self.led_pixel_spacing = 1
        self.border_size = 1
        self.width = (self.matrix_options.cols * (self.led_pixel_size + self.led_pixel_spacing) +
                      self.led_pixel_spacing) + self.border_size * 2
        self.height = (self.matrix_options.rows * (self.led_pixel_size + self.led_pixel_spacing) +
                       self.led_pixel_spacing) + self.border_size * 2
        self.pixel_shape = PixelShape.ROUND_RECT
        self.brightness_adjustment = 1.0  # 1.5


# noinspection PyPep8Naming
# we are mocking the method names from the rgbmatrix library
class VirtualFrameCanvas:

    def __init__(self):
        self.logger = logging.getLogger("VirtualFrameCanvas")
        self.image: Image = None
        self.options: Optional[VirtualRGBMatrixOptions] = None
        self.offset_x = 0
        self.offset_y = 0

    @staticmethod
    def _pil_image_to_surface(pil_image: Image):
        """
        from https://stackoverflow.com/questions/25202092/pil-and-pygame-image
        converting a PIL Image to a Pygame Surface
        :param pil_image: the PIL image
        :return: a pygame surface
        """
        return pygame.image.fromstring(pil_image.tobytes(), pil_image.size, pil_image.mode).convert()

    def SetImage(self, image: Image, offset_x: int = 0, offset_y: int = 0):
        self.image = image
        self.offset_x = offset_x
        self.offset_y = offset_y


# noinspection PyPep8Naming,PyMethodMayBeStatic
# we are mocking the method names from the rgbmatrix library
class VirtualRGBMatrix:

    def __init__(self, options: VirtualRGBMatrixOptions = None):
        self.logger = logging.getLogger("VirtualRGBMatrix")
        self.logger.info("Initializing")
        pygame.init()
        if not options:
            self.logger.error("Missing RGBMatrixOptions")

        self.matrix_options: VirtualRGBMatrixOptions = options
        self.window_specs = WindowSpecs(matrix_options=self.matrix_options)
        self._create_pygame_window()
        pygame.display.update()

    def _create_pygame_window(self):
        width = self.window_specs.width
        height = self.window_specs.height
        vsync = 0
        self.logger.info(f"Creating Pygame window at size {width} x {height} with vsync {vsync}")
        self.pygame_window = pygame.display.set_mode((self.window_specs.width, self.window_specs.height),
                                                     vsync=vsync)
        pygame.display.set_caption("Virtual LED Display")

    def CreateFrameCanvas(self) -> VirtualFrameCanvas:
        # self.logger.info("Creating frame canvas")
        frame_canvas = VirtualFrameCanvas()
        return frame_canvas

    @staticmethod
    def adjust_brightness(colors: tuple[int, int, int], adjustment: float) -> tuple[int, int, int]:
        def adjust_fn(x): return max(0, min(255, 255 - int((255 - x) / adjustment)))
        new_colors = (adjust_fn(colors[0]), adjust_fn(colors[1]), adjust_fn(colors[2]))
        return new_colors

    @staticmethod
    def _get_image_pixel(image: Image, x: int, y: int) -> tuple[int, int, int] or tuple[int, int, int, int]:
        if 0 <= x < image.size[0] and 0 <= y < image.size[1]:
            return image.getpixel((x, y))
        else:
            return 0, 0, 0

    def SwapOnVSync(self, frame_canvas: VirtualFrameCanvas) -> VirtualFrameCanvas:
        # draw the frame canvas to the window
        image = frame_canvas.image
        surface = pygame.display.get_surface()
        spacing = self.window_specs.led_pixel_spacing
        pix_size = self.window_specs.led_pixel_size
        pixel_shape = self.window_specs.pixel_shape
        half_pixel = pix_size / 2
        pix_radius = pix_size - half_pixel

        # clear surface
        surface.fill((0, 0, 0))
        # pygame.draw.rect(surface, (0, 0, 0), (0, 0, self.matrix_options.rows))

        # draw LED equivalents of image pixels
        for y in range(0, self.matrix_options.rows):
            offset_y = (pix_size + spacing) * y + spacing + self.window_specs.border_size
            for x in range(0, self.matrix_options.cols):
                offset_x = (pix_size + spacing) * x + spacing + self.window_specs.border_size
                colors = self.adjust_brightness(colors=self._get_image_pixel(image, x, y),
                                                adjustment=self.window_specs.brightness_adjustment)
                if pixel_shape == PixelShape.ROUND:
                    pygame.draw.circle(surface, colors, (offset_x + half_pixel, offset_y + half_pixel),
                                       pix_radius)
                elif pixel_shape == PixelShape.ROUND_RECT:
                    pygame.draw.rect(surface, colors, (offset_x, offset_y, pix_size, pix_size), border_radius=3)
                else:  # pixel_shape == PixelShape.SQUARE
                    pygame.draw.rect(surface, colors, (offset_x, offset_y, pix_size, pix_size))

        # swap it over
        pygame.event.get()  # discarding these for now
        pygame.display.flip()
        return self.CreateFrameCanvas()
