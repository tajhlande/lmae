import threading

from lmae_core import parse_matrix_options_command_line
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from lmae_animation import LinearMove, Sequence
from lmae_module import AppModule, SingleStageRenderLoopAppModule

from threading import Thread
import collections
import logging
import time

from pilmoji.source import AppleEmojiSource

from lmae_core import Stage, parse_matrix_options_command_line
from lmae_actor import StillImage, Text, EmojiText
from lmae_animation import LinearMove
from PIL import Image, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions

logging.basicConfig(level=logging.INFO, format='%(relativeCreated)9d %(name)10s [%(levelname)5s]: %(message)s')
logger = logging.getLogger("app_module_test")
logger.setLevel(logging.DEBUG)
print("LED Matrix Module Test")

options: RGBMatrixOptions = parse_matrix_options_command_line()
logger.info("Initializing matrix")
matrix = RGBMatrix(options=options)


# set up stage
logger.debug("Setting up stage")


def kirby_movement(frame_number: int) -> tuple[int, int]:
    return frame_number % 86 - 22, 12


kirby = StillImage(name='Kirby', position=(20, 12), image=Image.open("images/kirby_22.png").convert('RGBA'))
kirby_move_dist = 64 - kirby.size[0]
kirby_anim = Sequence(name="Kirby Repeat", actor=kirby, repeat=True,
                      animations=[LinearMove(name='Kirby go right', actor=kirby,
                                             distance=(0, 64 - kirby_move_dist), duration=2.0),
                                  LinearMove(name='Kirby go left', actor=kirby,
                                             distance=(0, -64 + kirby_move_dist), duration=2.0)])
trees = StillImage(name='Trees', image=Image.open("images/trees-composite.png").convert('RGBA'))
grass = StillImage(name='Grass', image=Image.open("images/grass.png").convert('RGBA'))
words = Text(name='Text', text="Hello,\nworld!", position=(5, 5),
             font=ImageFont.truetype("fonts/et-bt6001-font/EtBt6001-JO47.ttf", 6),  # good option for fitting a lot
             color=(255, 255, 255, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)

sample_app = SingleStageRenderLoopAppModule()
sample_app.set_matrix(matrix, options=options)
sample_app.add_actors(trees, words, kirby, grass)
sample_app.add_animations(kirby_anim)


def stop_app(app: AppModule):
    logger.info("***** Press return to stop the app *****")
    input()
    logger.debug("Return pressed")
    app.stop()


def run_app(app: AppModule):
    logger.debug("run_app() called")
    app.prepare()

    logger.info("Starting stopper thread")
    stopper_thread = Thread(target=stop_app, args=[app])
    stopper_thread.start()

    logger.info("Running app")
    app_thread = Thread(target=app.run)
    app_thread.start()

    stopper_thread.join()
    app_thread.join()

    logger.debug("run_app() finished")


run_app(sample_app)

