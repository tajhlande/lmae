import curses
import logging
import time
from lmae.core import Stage, StillImage, MovingActor, Text, parse_matrix_options_command_line
from PIL import Image, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions

logging.basicConfig(level=logging.DEBUG)

stdscr = curses.initscr()

options: RGBMatrixOptions = parse_matrix_options_command_line()

matrix = RGBMatrix(options=options)
stage = Stage(matrix=matrix, matrix_options=options)


def kirby_movement(frame_number: int) -> tuple[int, int]:
    return frame_number % 86 - 22, 12


kirby = StillImage(name='Kirby', position=(20, 12), image=Image.open("images/kirby_22.png").convert('RGBA'))
moving_kirby = MovingActor(kirby, name="Moving Kirby", movement_function=kirby_movement)
trees = StillImage(name='Trees', image=Image.open("images/trees-composite.png").convert('RGBA'))
grass = StillImage(name='Grass', image=Image.open("images/grass.png").convert('RGBA'))
words = Text(name='Text', text="Hello, world!", position=(5, 5),
             # the following are the fonts native point sizes to avoid blurring
             # font=ImageFont.truetype("fonts/et-bt6001-font/EtBt6001-JO47.ttf", 12),
             # font=ImageFont.truetype("fonts/hardpixel-font/Hardpixel-nn51.otf", 14), # not a perfect fit
             # font=ImageFont.truetype("fonts/oseemono-font/Oseemono-V5Ez.ttf", 16),
             # font=ImageFont.truetype("fonts/poh-pixels-font/PohPixelsRegular-ljXw.ttf", 16),
             # font=ImageFont.truetype("fonts/sd-another-dimension-font/SdAnotherDimension-ljed.ttf", 10),
             # font=ImageFont.truetype("fonts/sparkly-font/SparklyFontRegular-zyA3.ttf", 8),  # placement is top line
             font=ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5),
             color=(255, 255, 255, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)
stage.actors.extend((trees, words, moving_kirby, grass))


print("Press CTRL-C to stop render loop")
i = 0
try:
    hz_pos =  curses.getsyx()
    while True:
        start_time = time.time()
        stage.render_frame(i)
        i = i + 1
        end_time = time.time()
        # if we are running faster than 120HZ, slow down
        time.sleep(max((1.0/120.0) - (end_time - start_time), 0))
        stdscr.addstr(hz_pos[0], hz_pos[1], f"{1/(end_time - start_time)} Hz    ")
        stdscr.refresh()
finally:
    curses.endwin()


