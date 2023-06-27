import logging
import time
from lmae.core import Stage, StillImage, Text, parse_matrix_options_command_line
from PIL import Image, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions

logging.basicConfig(level=logging.DEBUG)
options: RGBMatrixOptions = parse_matrix_options_command_line()

matrix = RGBMatrix(options=options)
stage = Stage(matrix=matrix, matrix_options=options)

kirby = StillImage(name='Kirby', position=(20, 12), image=Image.open("images/kirby_22.png").convert('RGBA'))
trees = StillImage(name='Trees', image=Image.open("images/trees-composite.png").convert('RGBA'))
grass = StillImage(name='Grass', image=Image.open("images/grass.png").convert('RGBA'))
words = Text(name='Text', text="Hello, world!", position=(5, 10),
             # the following are the fonts native point sizes to avoid blurring
             # font=ImageFont.truetype("fonts/et-bt6001-font/EtBt6001-JO47.ttf", 12),
             # font=ImageFont.truetype("fonts/hardpixel-font/Hardpixel-nn51.otf", 14), # not a perfect fit
             # font=ImageFont.truetype("fonts/oseemono-font/Oseemono-V5Ez.ttf", 16),
             # font=ImageFont.truetype("fonts/poh-pixels-font/PohPixelsRegular-ljXw.ttf", 16),
             # font=ImageFont.truetype("fonts/sd-another-dimension-font/SdAnotherDimension-ljed.ttf", 10),
             font=ImageFont.truetype("fonts/sparkly-font/SparklyFontRegular-zyA3.ttf", 12), # placement is top line
             color=(255, 255, 255, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)
stage.actors.extend((trees, words, kirby, grass))

stage.render_frame()

print("Press CTRL-C to stop sample")
while True:
    time.sleep(1)
