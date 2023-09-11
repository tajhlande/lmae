import sys

from lmae_module import AppModule
import asyncio
import logging
import configparser
from lmae_core import parse_matrix_options_command_line
from rgbmatrix import RGBMatrix, RGBMatrixOptions

matrix: RGBMatrix
logger: logging.Logger
matrix_options: RGBMatrixOptions


def app_setup():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)12s [%(levelname)5s]: %(message)s')
    global logger
    logger = logging.getLogger("app_runner")
    logger.setLevel(logging.DEBUG)
    print("App Runner")

    global matrix_options
    matrix_options = parse_matrix_options_command_line()
    logger.info("Initializing matrix")
    global matrix
    matrix = RGBMatrix(options=matrix_options)


# borrowed from StackOverflow:
# https://stackoverflow.com/questions/58454190/python-async-waiting-for-stdin-input-while-doing-other-stuff
async def async_input(string: str) -> str:
    await asyncio.to_thread(sys.stdout.write, f'{string} ')
    return (await asyncio.to_thread(sys.stdin.readline)).rstrip('\n')


async def stop_app(app: AppModule):
    logger.info("***** Press return to stop the app *****")
    await async_input('')
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


def start_app(app: AppModule):
    asyncio.run(run_app(app))


env_config = configparser.ConfigParser()
env_config.read('env.ini')
