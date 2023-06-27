import collections
import curses
import logging
import math
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
previous_elapsed_times = collections.deque((), 100)
max_frame_rate = 120
min_time_per_frame = 1.0 / max_frame_rate
try:
    curses_window = curses.newwin(1, 7)
    hz_pos = curses_window.getyx()
    last_time = time.time()
    while True:
        # render the frame
        stage.render_frame(i)
        i = i + 1

        # calculate the frame rate and render that
        average_time = 1 if len(previous_elapsed_times) == 0 \
            else sum(previous_elapsed_times) / len(previous_elapsed_times)
        curses_window.erase()
        curses_window.addstr(hz_pos[0], hz_pos[1], f"{round(1.0 / average_time)} Hz")
        curses_window.refresh()
        render_end_time = time.time()

        # if we are rendering faster than max frame rate, slow down
        elapsed_render_time = render_end_time - last_time
        if elapsed_render_time < min_time_per_frame:
            time.sleep(round((min_time_per_frame - elapsed_render_time) * 100) / 100)

        # record total elapsed time
        end_time = time.time()
        elapsed_time = end_time - last_time
        previous_elapsed_times.appendleft(elapsed_time)
        last_time = end_time

finally:
    curses.endwin()


