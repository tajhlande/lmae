import os, unittest

from context import lmae
from lmae.core import Canvas
from lmae.actor import Text
from PIL import Image, ImageFont, ImageDraw

class TextTest(unittest.TestCase):
    def test_text_dimensions_change(self):
        font = ImageFont.truetype(os.path.join(os.path.dirname(__file__),
                   "../examples/fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf"), 5)
        canvas = Canvas()
        text = Text(font=font, color=(224, 224, 224, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)
        sizing_image = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(sizing_image)
        draw.rectangle((0, 0, 64, 32), fill=(0, 0, 0, 0))


        base_string = "abcdefghijklmnopqrstuvwxyz"
        for i in range(1, len(base_string)):
            canvas.blank()
            text_string = base_string[:i]
            text.set_text(text_string)
            print(f"for {i=}, {text_string=}")
            text.render(canvas=canvas)
            text_bbox = draw.textbbox(xy=(0, 0), text=text_string, font=font, stroke_width=1)
            text_dimensions = text_bbox[2:4]

            for x in range(text_dimensions[0] + 1, canvas.size[0]):
                for y in range(text_dimensions[1] + 1, canvas.size[1]):
                    self.assertEqual((0, 0, 0, 255), canvas.image.getpixel((x, y)))

        for i in range (len(base_string)-2, 0, -1):
            canvas.blank()
            text_string = base_string[:i]
            text.set_text(text_string)
            print(f"for {i=}, {text_string=}")
            text.render(canvas=canvas)
            text_bbox = draw.textbbox(xy=(0, 0), text=text_string, font=font, stroke_width=1)
            text_dimensions = text_bbox[2:4]

            for x in range(text_dimensions[0] + 1, canvas.size[0]):
                for y in range(text_dimensions[1] + 1, canvas.size[1]):
                    self.assertEqual((0, 0, 0, 255), canvas.image.getpixel((x, y)))

