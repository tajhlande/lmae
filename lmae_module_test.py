from lmae_core import parse_matrix_options_command_line
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from lmae_module import AppModule, SingleStageRenderLoopAppModule

import asyncio
import collections
import logging
import time

from pilmoji.source import AppleEmojiSource

from lmae_core import Stage, StillImage, MovingActor, Text, EmojiText, parse_matrix_options_command_line
from PIL import Image, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions

logging.basicConfig(level=logging.INFO, format='%(relativeCreated)9d %(name)10s [%(levelname)5s]: %(message)s')
logger = logging.getLogger("app_module_test")
logger.setLevel(logging.DEBUG)
print("LED Matrix Module Test")

options: RGBMatrixOptions = parse_matrix_options_command_line()
matrix = RGBMatrix(options=options)


# set up stage
def kirby_movement(frame_number: int) -> tuple[int, int]:
    return frame_number % 86 - 22, 12


kirby = StillImage(name='Kirby', position=(20, 12), image=Image.open("images/kirby_22.png").convert('RGBA'))
moving_kirby = MovingActor(kirby, name="Moving Kirby", movement_function=kirby_movement)
trees = StillImage(name='Trees', image=Image.open("images/trees-composite.png").convert('RGBA'))
grass = StillImage(name='Grass', image=Image.open("images/grass.png").convert('RGBA'))
words = Text(name='Text', text="Hello,\nworld!", position=(5, 5),
             font=ImageFont.truetype("fonts/et-bt6001-font/EtBt6001-JO47.ttf", 6),  # good option for fitting a lot
             color=(255, 255, 255, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)

sample_app = SingleStageRenderLoopAppModule()
sample_app.set_matrix(matrix, options=options)
sample_app.add_actors(trees, words, moving_kirby, grass)


async def stop_app(app: AppModule):
    logger.debug("Press return to stop")
    await input()
    logger.debug("Return pressed")
    app.stop()


async def run_app(app: AppModule):
    logger.debug("run_app() called")
    app_run_task = asyncio.create_task(app.run())
    app_stop_task = asyncio.create_task(stop_app(app))
    logger.debug("Awaiting app run task")
    await app_run_task
    logger.debug("Awaiting app stop task")
    await app_stop_task
    logger.debug("run_app() finished")


asyncio.run(run_app(sample_app))

