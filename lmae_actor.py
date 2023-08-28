import json

from PIL import Image, ImageFont
from pilmoji import Pilmoji
from pilmoji.source import EmojiCDNSource, MicrosoftEmojiSource

from lmae_core import Actor, _get_sequential_name, Canvas, CompositeActor, logger


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

    def set_from_file(self, filename):
        self.image = Image.open(filename)
        if not self.image.mode == 'RGBA':
            self.image = self.image.convert('RGBA')
        self.size = self.image.size

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
        self.selected = selected
        if self.sheet and self.selected and self.selected in self.spec:
            self.size = tuple(int(i) for i in self.spec[self.selected]['size'])
        else:
            self.size = (0, 0)
        self.changes_since_last_render = True

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
        self.text = text
        self.color = color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width

    def set_text(self, text: str):
        if not text == self.text:
            self.changes_since_last_render = True
        self.text = text

    def render(self, canvas: Canvas):
        if self.text:
            draw = canvas.image_draw
            # logging.debug(f"Drawing text at {self.position} with color {self.color}, font {self.font.getname()}, "
            #               f"stroke_fill {self.stroke_color} and stroke_width {self.stroke_width}: '{self.text}'")
            draw.text(self.position, self.text, fill=self.color, font=self.font,
                      stroke_fill=self.stroke_color, stroke_width=self.stroke_width)

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

    def set_position(self, position: tuple[int, int]):
        self.position = position
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
        self.logger.debug(f"Drawing rect at {self.position}:{opposite_corner} with color {self.color},  "
                      f"outline_color {self.outline_color} and outline_width {self.outline_width}")
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
        self.color = color
        self.changes_since_last_render = True

    def set_start(self, start: tuple[int, int]):
        self.start = start
        self.calc_size_and_position()
        self.changes_since_last_render = True

    def set_end(self, end: tuple[int, int]):
        self.end = end
        self.calc_size_and_position()
        self.changes_since_last_render = True

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
    Position and size here are for the entire croppable area, and crop_area is the part
    you wish to be visible.
    Default crop area is a central 1/4 of the total image.
    """
    def __init__(self, name: str = None, child: Actor = None,
                 position: tuple[int, int] = (0, 0), size: tuple[int, int] = (64, 32),
                 crop_area: tuple[int, int, int, int] = (16, 8, 47, 23)):
        name = name or _get_sequential_name("CropMask")
        super().__init__(name, child=child, position=position)
        self.size = size
        self.crop_canvas = Canvas(name=f"{self.name} crop canvas", background_fill=True, size=size)
        self.crop_rect_1 = (0, 0, 0, 0)
        self.crop_rect_2 = (0, 0, 0, 0)
        self.crop_rect_3 = (0, 0, 0, 0)
        self.crop_rect_4 = (0, 0, 0, 0)
        self.crop_area = (16, 8, 47, 23)
        self.set_crop_area(crop_area)

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

    def render(self, canvas: Canvas):
        if self.child:
            # clear the crop canvas
            self.crop_canvas.blank()

            # ask the child to render into the crop canvas
            self.child.render(self.crop_canvas)

            # apply the crop by blanking out the relevant parts
            crop_black = (0, 0, 0, 0)
            draw = self.crop_canvas.image_draw
            for rect in [self.crop_rect_1, self.crop_rect_2, self.crop_rect_3, self.crop_rect_4]:
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
                if width >= 0 and height >= 0:  # 0 actually means draw a single pixel width/height
                    draw.rectangle(rect, fill=crop_black, width=1)

            # composite downwards
            canvas.image.alpha_composite(self.crop_canvas.image, dest=self.position)

        self.changes_since_last_render = False
