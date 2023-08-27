import asyncio
import logging
import sys

from PIL import Image, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions

from lmae_core import parse_matrix_options_command_line
from lmae_actor import StillImage, Text
from lmae_animation import LinearMove, Sequence
from lmae_module import AppModule, SingleStageRenderLoopAppModule

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


kirby = StillImage(name='Kirby', position=(0, 12), image=Image.open("images/kirby_22.png").convert('RGBA'))
kirby_move_dist = 64 - kirby.size[0]
logger.debug(f"Kirby move distance is {kirby_move_dist}")
kirby_go_right = LinearMove(name='Kirby go right', actor=kirby, distance=(kirby_move_dist, 0), duration=2.0)
kirby_go_left = LinearMove(name='Kirby go left', actor=kirby, distance=(-kirby_move_dist, 0), duration=2.0)
kirby_anim = Sequence(name="Kirby Repeat", actor=kirby, repeat=True, animations=[kirby_go_right, kirby_go_left])
trees = StillImage(name='Trees', image=Image.open("images/trees-composite.png").convert('RGBA'))
grass = StillImage(name='Grass', image=Image.open("images/grass.png").convert('RGBA'))
words = Text(name='Text', text="Hello,\nworld!", position=(5, 5),
             font=ImageFont.truetype("fonts/et-bt6001-font/EtBt6001-JO47.ttf", 6),  # good option for fitting a lot
             color=(255, 255, 255, 255), stroke_color=(0, 0, 0, 255), stroke_width=1)

sample_app = SingleStageRenderLoopAppModule()
sample_app.set_matrix(matrix, options=options)
sample_app.add_actors(trees, words, kirby, grass)
sample_app.add_animations(kirby_anim)


# borrowed from StackOverflow:
# https://stackoverflow.com/questions/58454190/python-async-waiting-for-stdin-input-while-doing-other-stuff
async def async_input(string: str) -> str:
    await asyncio.to_thread(sys.stdout.write, f'{string} ')
    return (await asyncio.to_thread(sys.stdin.readline)).rstrip('\n')


async def stop_app(app: AppModule):
    logger.info("***** Press return to stop the app *****")
    await async_input('>')
    logger.debug("Return pressed")
    app.stop()


async def run_app(app: AppModule):
    logger.debug("run_app() called")
    app.prepare()

    logger.info("Creating stopper task")
    stopper_task = asyncio.create_task(stop_app(app))

    logger.info("Creating app runner task")
    app_runner_task = asyncio.create_task(app.run())

    await asyncio.gather(stopper_task, app_runner_task)

    logger.debug("run_app() finished")

asyncio.run(run_app(sample_app))

