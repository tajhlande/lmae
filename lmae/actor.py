import json
import logging

from PIL import Image, ImageFont, ImageDraw
from pilmoji import Pilmoji
from pilmoji.source import EmojiCDNSource, MicrosoftEmojiSource

from lmae.core import Actor, _get_sequential_name, Canvas, CompositeActor, logger


class StillImage(Actor):
    """
    An unchanging image that can position itself on a stage
    """
    def __init__(self, name: str = None, position: tuple[int, int] = (0, 0), image: Image = None):
        """
        Initialize a still image actor
        :param name: The name of this image actor
        :param position:The initial position of this still image actor
        :param image: The PIL image for this image actor
        """
        name = name or _get_sequential_name("StillImage")  # 'StillImage_' + f'{randrange(65536):04X}'
        super().__init__(name=name, position=position)
        self.image = image
        self.size = self.image.size if self.image else (0, 0)

    def set_from_image(self, image: Image):
        self.image = image
        if self.image:
            if not self.image.mode == 'RGBA':
                self.image = self.image.convert('RGBA')
            self.size = self.image.size
        else:
            self.size = (0, 0)
        self.changes_since_last_render = True

    def set_from_file(self, filename: str):
        self.set_from_image(Image.open(filename))

    def render(self, canvas: Canvas):
        if self.image:
            canvas.image.alpha_composite(self.image, dest=self.position)
        self.changes_since_last_render = False


class SpriteImage(Actor):
    """
    An image that is drawn as a specific crop from a sprite sheet image
    """
    def __init__(self, name: str = None, position: tuple[int, int] = (0, 0),
                 sheet: Image = None, spec=None,
                 selected: str = None):
        """
        Initialize a sprite image actor
        :param name: The name of this actor
        :param position: The initial position of this sprite on the stage
        :param sheet: The sprite sheet image
        :param spec: The sprite specification: a dict of objects with position and size info
        :param selected: Which sprite to display first, by name in the spec
        """
        if spec is None:
            spec = dict()
        name = name or _get_sequential_name("SpriteImage")  # 'SpriteImage_' + f'{randrange(65536):04X}'
        super().__init__(name=name, position=position)
        self.sheet = sheet
        self.spec = spec
        self.selected = None
        self.size = (0, 0)
        self.set_sprite(selected)

    def set_sprite(self, selected: str):
        # logger.debug(f"Setting sprite to {selected}")
        if selected != self.selected:
            self.changes_since_last_render = True
        self.selected = selected
        if self.sheet and self.selected and self.selected in self.spec:
            self.size = tuple(int(i) for i in self.spec[self.selected]['size'])
        else:
            self.size = (0, 0)

    def set_from_file(self, image_filename, spec_filename):
        logger.debug(f"Loading sprite sheet image from {image_filename}")
        self.sheet = Image.open(image_filename).convert('RGBA')

        logger.debug(f"Loading spec file from {spec_filename}")
        with open(spec_filename) as spec_file:
            self.spec = json.load(spec_file)

    def render(self, canvas: Canvas):
        if self.sheet and self.selected in self.spec:
            entry = self.spec[self.selected]
            sheet_position = tuple(int(i) for i in entry['position'])
            size = tuple(int(i) for i in entry['size'])  # may be superfluous if size has already been stored correctly
            bounds = (sheet_position[0], sheet_position[1],
                      sheet_position[0] + size[0], sheet_position[1] + size[1])
            # logger.debug(f"Rendering sprite at {self.position} from sheet at {sheet_position} and size {size}")
            canvas.image.alpha_composite(self.sheet, dest=self.position, source=bounds)
        self.changes_since_last_render = False


class MultiFrameImage(Actor):

    def __init__(self, name: str = None, position: tuple[int, int] = (0, 0), images: list[Image] = None):
        name = name or _get_sequential_name("MultiFrameImage")
        super().__init__(name=name, position=position)
        self.images: list[Image] = images or []
        self.current_frame: int = 0

    def set_frame(self, frame_number: int):
        if self.images and 0 <= frame_number < len(self.images):
            if self.current_frame != frame_number:
                self.logger.debug(f"Updating to frame {frame_number}")
            self.current_frame = frame_number
            self.changes_since_last_render = True
        else:
            self.logger.warning(f"Asked to set invalid frame number {frame_number}. "
                                f"There are {len(self.images)} present.")

    def render(self, canvas: Canvas):
        if 0 <= self.current_frame < len(self.images):
            canvas.image.alpha_composite(self.images[self.current_frame], dest=self.position)
        self.changes_since_last_render = False


class Text(Actor):
    """
    Text that renders on a stage
    """

    def __init__(self,
                 font: ImageFont,
                 name: str = None,
                 position: tuple[int, int] = (0, 0),
                 text: str = None,
                 color: tuple[int, int, int] or tuple[int, int, int, int] = (255, 255, 255, 255),
                 stroke_color: tuple[int, int, int] or tuple[int, int, int, int] = (0, 0, 0, 255),
                 stroke_width: int = 0):
        name = name or _get_sequential_name("Text")  # 'Text_' + f'{randrange(65536):04X}'
        super().__init__(name=name, position=position)
        self.font = font
        self.color = color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.logger = logging.getLogger(name)
        self.has_warned_about_image_mode = False
        self.rendered_text: Image = None
        self.text: str or None = None
        if text:
            self.set_text(text)

    def set_color(self, color: tuple[int, int, int] or tuple[int, int, int, int]):
        if self.color != color:
            self.color = color
            self._prerender_text()
            self.changes_since_last_render = True

    def _prerender_text(self):
        # measure size of text
        image = Image.new('RGBA', (64, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        # assume font is TTF for now, because the doc for this function says that is required
        text_bbox = draw.textbbox(xy=(0, 0), text=self.text, font=self.font, stroke_width=self.stroke_width)
        self.size = text_bbox[2:4]
        # self.logger.debug(f"Measured rendered text size at {self.size}. text(len {len(self.text)}): <{self.text}>")

        # account for stroke width
        self.size = (self.size[0] + self.stroke_width * 2, self.size[1] + self.stroke_width * 2)

        # render into the image we'll keep
        self.rendered_text = Image.new('RGBA', self.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(self.rendered_text)
        draw.text((self.stroke_width, self.stroke_width), self.text, fill=self.color, font=self.font,
                  stroke_fill=self.stroke_color, stroke_width=self.stroke_width)

    def set_text(self, text: str):
        if text != self.text:
            self.text = text
            self._prerender_text()
            self.changes_since_last_render = True

    def render(self, canvas: Canvas):
        if self.text:
            if self.rendered_text:
                render_pos = (self.position[0] - self.stroke_width, self.position[1] - self.stroke_width)
                canvas.image.alpha_composite(self.rendered_text, dest=render_pos)

            # previous method
            # # self.logger.debug(f"Rendering at {self.position}")
            # draw = canvas.image_draw
            # # logging.debug(f"Drawing text at {self.position} with color {self.color}, font {self.font.getname()}, "
            # #               f"stroke_fill {self.stroke_color} and stroke_width {self.stroke_width}: '{self.text}'")
            # if canvas.image.mode is not "RGBA" and not self.has_warned_about_image_mode:
            #     logging.warning(f"Text render canvas was '{canvas.image.mode}' and not 'RGBA' as expected")
            #     self.has_warned_about_image_mode = True
            # draw.text(self.position, self.text, fill=self.color, font=self.font,
            #           stroke_fill=self.stroke_color, stroke_width=self.stroke_width)
        else:
            # self.logger.debug("No text to render")
            pass
        self.changes_since_last_render = False


class EmojiText(Actor):
    """
    Text that could contain emoji and that renders on a stage
    """

    def __init__(self,
                 text_font: ImageFont,
                 emoji_source: EmojiCDNSource = MicrosoftEmojiSource,
                 name: str = None,
                 position: tuple[int, int] = (0, 0),
                 text: str = None,
                 color: tuple[int, int, int] or tuple[int, int, int, int] = (255, 255, 255, 255),
                 stroke_color: tuple[int, int, int] or tuple[int, int, int, int] = (0, 0, 0, 255),
                 stroke_width: int = 0,
                 emoji_scale_factor: float = 1.0,
                 emoji_position_offset: tuple[int, int] = (0, 0)):
        name = name or _get_sequential_name("EmojiText")  # 'Text_' + f'{randrange(65536):04X}'
        super().__init__(name=name, position=position)
        self.emoji_source = emoji_source
        self.text_font = text_font
        self.text = text
        self.color = color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.emoji_scale_factor = emoji_scale_factor
        self.emoji_position_offset = emoji_position_offset
        self.canvas = None  # we will prerender on this
        self.pre_render()

    def set_text(self, text: str):
        if not text == self.text:
            self.changes_since_last_render = True
            self.pre_render()
        self.text = text

    def pre_render(self):
        # logger.debug(f"Pre-rendering emoji text at {self.position} with color {self.color}, "
        #              f"font {self.font.getname()}: '{self.text}'")
        self.canvas = Canvas(background_fill=False)
        if self.text:
            with Pilmoji(self.canvas.image, source=self.emoji_source) as pilmoji:
                pilmoji.text(self.position, self.text, self.color, self.text_font,
                             stroke_width=self.stroke_width, stroke_fill=self.stroke_color,
                             emoji_scale_factor=self.emoji_scale_factor,
                             emoji_position_offset=self.emoji_position_offset)

    def render(self, canvas: Canvas):
        if self.text:
            # logger.debug(f"Drawing pre-rendered emoji text at {self.position} with color {self.color}, "
            #              f"font {self.font.getname()}: '{self.text}'")

            canvas.image.alpha_composite(self.canvas.image, dest=(0, 0))
        self.changes_since_last_render = False


class Rectangle(Actor):
    """
    A rectangle that draws itself on a stage
    """

    def __init__(self,
                 name: str = None,
                 position: tuple[int, int] = (0, 0),
                 size: tuple[int, int] = (0, 0),
                 color: tuple[int, int, int] or tuple[int, int, int, int] = (255, 255, 255, 255),
                 outline_color: tuple[int, int, int] or tuple[int, int, int, int] = (0, 0, 0, 255),
                 outline_width: int = 0):
        name = name or _get_sequential_name("Rectangle")  # 'Text_' + f'{randrange(65536):04X}'
        super().__init__(name=name, position=position)
        self.size = size
        self.color = color
        self.outline_color = outline_color
        self.outline_width = outline_width

    def set_color(self, color: tuple[int, int, int] or tuple[int, int, int, int]):
        self.color = color
        self.changes_since_last_render = True

    def set_outline_color(self, outline_color: tuple[int, int, int] or tuple[int, int, int, int]):
        self.outline_color = outline_color
        self.changes_since_last_render = True

    def set_size(self, size: tuple[int, int]):
        self.size = size
        self.changes_since_last_render = True

    def set_outline_width(self, outline_width: int):
        self.outline_width = outline_width
        self.changes_since_last_render = True

    def render(self, canvas: Canvas):
        draw = canvas.image_draw
        opposite_corner = tuple(map(lambda i, j: i + j, self.position, self.size))
        # self.logger.debug(f"Drawing rect at {self.position}:{opposite_corner} with color {self.color},  "
        #                   f"outline_color {self.outline_color} and outline_width {self.outline_width}")
        draw.rectangle(self.position + opposite_corner, fill=self.color, outline=self.outline_color,
                       width=self.outline_width)

        self.changes_since_last_render = False


class Line(Actor):
    """
    A line that draws itself on a stage
    """

    def __init__(self,
                 name: str = None,
                 start: tuple[int, int] = (0, 0),
                 end: tuple[int, int] = (0, 0),
                 color: tuple[int, int, int] or tuple[int, int, int, int] = (255, 255, 255, 255)):
        name = name or _get_sequential_name("Line")
        super().__init__(name=name, position=start)
        self.start = start
        self.end = end
        self.calc_size_and_position()
        self.color = color

    def set_color(self, color: tuple[int, int, int] or tuple[int, int, int, int]):
        if color != self.color:
            self.changes_since_last_render = True
        self.color = color

    def set_start(self, start: tuple[int, int]):
        if start != self.start:
            self.changes_since_last_render = True
        self.start = start
        self.calc_size_and_position()

    def set_end(self, end: tuple[int, int]):
        if end != self.end:
            self.changes_since_last_render = True
        self.end = end
        self.calc_size_and_position()

    def calc_size_and_position(self):
        self.size = abs(self.start[0] - self.end[0]), abs(self.start[1] - self.end[1])
        self.set_position((min(self.start[0], self.end[0]), min(self.start[1], self.end[1])))

    def render(self, canvas: Canvas):
        draw = canvas.image_draw
        # self.logger.debug(f"Drawing line from {self.start} to {self.end} with color {self.color}")
        draw.line((self.start, self.end), fill=self.color, width=1)

        self.changes_since_last_render = False


class CropMask(CompositeActor):
    """
    Composite actor that will crop another actor's rendering to a defined rectangle.
    Crop area is inclusive of those pixels.
    Position and size here are for the entire crop-able area, and crop_area is the part
    you wish to be visible.
    Default crop area is a central 1/4 of the total image.
    """
    def __init__(self, name: str = None, child: Actor = None,
                 position: tuple[int, int] = (0, 0), size: tuple[int, int] = (64, 32),
                 crop_area: tuple[int, int, int, int] = (16, 8, 47, 23)):
        name = name or _get_sequential_name("CropMask")
        super().__init__(name, child=child, position=position)
        self.logger = logging.getLogger(name)
        self.size = size
        self.crop_canvas = Canvas(name=f"{self.name}_crop_Canvas", background_fill=False, size=size)
        self.crop_rect_1 = (0, 0, 0, 0)
        self.crop_rect_2 = (0, 0, 0, 0)
        self.crop_rect_3 = (0, 0, 0, 0)
        self.crop_rect_4 = (0, 0, 0, 0)
        self.crop_area = (16, 8, 47, 23)
        self.set_crop_area(crop_area)
        # self.logger.debug(f"Set crop area to {self.crop_area}")

    def set_crop_area(self, crop_area: tuple[int, int, int, int]):
        if self.crop_area != crop_area:
            self.changes_since_last_render = True
        self.crop_area = crop_area

        """
        Blanking out cropped out areas with black + alpha 0 by drawing 4 rectangles as follows:

        1111111111111111
        2222C+++++++3333
        2222+++++++D3333
        4444444444444444

        where the area with +,C, & D represents the child's retained drawing area, and 1-4 represent the four
        rectangles around the crop area that we will draw.
        C = the first two coordinates of the crop area
        D = the second two coordinates of the crop area
        """
        self.crop_rect_1 = (self.position[0], self.position[1], self.size[0] - 1, self.crop_area[1] - 1)
        self.crop_rect_2 = (self.position[0], self.crop_area[1], self.crop_area[0] - 1, self.crop_area[3])
        self.crop_rect_3 = (self.crop_area[2] + 1, self.crop_area[1], self.size[0] - 1, self.crop_area[3])
        self.crop_rect_4 = (self.position[0], self.crop_area[3] + 1, self.size[0] - 1, self.size[1] - 1)

        # self.logger.debug(f"Crop rectangle 1: {self.crop_rect_1}")
        # self.logger.debug(f"Crop rectangle 2: {self.crop_rect_2}")
        # self.logger.debug(f"Crop rectangle 3: {self.crop_rect_3}")
        # self.logger.debug(f"Crop rectangle 4: {self.crop_rect_4}")

    def render(self, canvas: Canvas):
        if self.child:
            # self.logger.debug(f"Rendering at {self.crop_area}")
            # set up the crop canvas
            self.crop_canvas = Canvas(name=f"{self.name}_crop_Canvas", background_fill=False, size=self.size)

            # ask the child to render into the crop canvas
            self.child.render(self.crop_canvas)

            # apply the crop by blanking out the relevant parts with full alpha
            crop_black = (0, 0, 0, 0)
            draw = self.crop_canvas.image_draw
            for rect in [self.crop_rect_1, self.crop_rect_2, self.crop_rect_3, self.crop_rect_4]:
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
                if width >= 0 and height >= 0:  # 0 actually means draw a single pixel width/height
                    # self.logger.debug(f"Drawing crop rect ({rect})")
                    draw.rectangle(rect, fill=crop_black, width=1)
                else:
                    # self.logger.debug(f"Not drawing crop rect ({rect}) because it has negative width or height")
                    pass

            # composite the crop canvas into the parameter canvas
            canvas.image.alpha_composite(self.crop_canvas.image, dest=self.position)
        else:
            # self.logger.warning("No child to render")
            pass
        self.changes_since_last_render = False


class GradientRectangle(Actor):
    """
    A filled rectangle drawn as a gradient shaded from top to bottom.
    """
    def __init__(self, name: str = None, position: tuple[int, int] = (0, 0), size: tuple[int, int] = (63, 31),
                 top_color: tuple[int, int, int] or tuple[int, int, int, int] = (255, 255, 255, 255),
                 bottom_color: tuple[int, int, int] or tuple[int, int, int, int] = (0, 0, 0, 0)):
        """

        :param name: Optional name for this actor. If not set, a name will be automatically generated.
        :param position: The position of the upper left corner
        :param size: The size of the rectangle
        :param top_color: The color at the top of the rectangle. Can be RGB or RGBA/
        :param bottom_color: The color at the bottom of the rectangle.
        """
        name = name or _get_sequential_name("GradientRectangle")
        super().__init__(name, position)
        self.size = size
        self.top_color = top_color
        self.bottom_color = bottom_color

    def set_top_color(self, new_color: tuple[int, int, int] or tuple[int, int, int, int]):
        if self.top_color != new_color:
            self.changes_since_last_render = True
        self.top_color = new_color

    def set_bottom_color(self, new_color: tuple[int, int, int] or tuple[int, int, int, int]):
        if self.bottom_color != new_color:
            self.changes_since_last_render = True
        self.bottom_color = new_color

    def render(self, canvas: Canvas):
        draw = canvas.image_draw
        y_start = self.position[1]
        y_end = self.position[1] + self.size[1]
        x_start = self.position[0]
        x_end = self.position[0] + self.size[0]

        for y in range(y_start, y_end):
            gradient_factor = y * 1.0 / self.size[1]
            color = self.interpolate_color(self.top_color, self.bottom_color, gradient_factor)
            draw.line((x_start, y, x_end, y), fill=color, width=1)

        self.changes_since_last_render = False

    @staticmethod
    def interpolate_color(start_color: tuple[int, int, int] or tuple[int, int, int, int],
                          end_color: tuple[int, int, int] or tuple[int, int, int, int],
                          blend_factor: float) -> tuple[int, int, int, int]:
        """
        Interpolate two RGB or RGBA colors
        :param start_color: The color to start with.
        :param end_color: The color to end with.
        :param blend_factor: Between 0.0 and 1.0, how much of start and end colors to blend.
        0.0 is 100% of start, 0% of end.
        0.5 is 50% of start, 50% of end.
        1.0 is 0% of start, 100% of end.
        :return: The blended RGBA color
        """
        inv_blend_factor = 1.0 - blend_factor
        blend_red = int(start_color[0] * inv_blend_factor + end_color[0] * blend_factor)
        blend_green = int(start_color[1] * inv_blend_factor + end_color[1] * blend_factor)
        blend_blue = int(start_color[2] * inv_blend_factor + end_color[2] * blend_factor)
        start_alpha = start_color[3] if len(start_color) == 4 else 255
        end_alpha = end_color[3] if len(end_color) == 4 else 255
        blend_alpha = int(start_alpha * inv_blend_factor + end_alpha * inv_blend_factor)
        return blend_red, blend_green, blend_blue, blend_alpha
