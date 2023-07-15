import threading

from lmae_core import parse_matrix_options_command_line
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from lmae_module import AppModule, SingleStageRenderLoopAppModule

from threading import Thread
import collections
import logging
import time

from pilmoji.source import AppleEmojiSource

from lmae_core import Stage, StillImage, SpriteImage, Text, parse_matrix_options_command_line
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


weather_sprite = SpriteImage(name='Weather Condition', position=((64-17)/2, (32-17)/2))
weather_sprite.set_from_file("images/weather-sprites.png", "images/weather-sprites.png")
weather_sprite.set_sprite("sunny")


def set_weather_sprite_frame(frame: int):
    frame_offset = frame % 1600
    frame_index = frame_offset / 100
    weather_sprite.set_sprite(weather_sprite.spec.keys[frame_index])


sample_app = SingleStageRenderLoopAppModule()
sample_app.set_matrix(matrix, options=options)
sample_app.add_actors(weather_sprite)
sample_app.set_pre_render_callback(set_weather_sprite_frame)


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
