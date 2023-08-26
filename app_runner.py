from lmae_module import AppModule
import asyncio
import logging
import os
import configparser
from lmae_core import parse_matrix_options_command_line
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from weather_app import WeatherApp

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)12s [%(levelname)5s]: %(message)s')
logger = logging.getLogger("app_runner")
logger.setLevel(logging.DEBUG)
print("App Runner")

options: RGBMatrixOptions = parse_matrix_options_command_line()
logger.info("Initializing matrix")
matrix = RGBMatrix(options=options)


async def stop_app(app: AppModule):
    logger.info("***** Press return to stop the app *****")
    input()
    logger.debug("Return pressed")
    app.stop()


def run_app(app: AppModule):
    logger.debug("run_app() called")
    app.prepare()

    logger.info("Creating stopper task")
    stopper_task = asyncio.create_task(stop_app(app))

    logger.info("Creating app runner task")
    app_runner_task = asyncio.create_task(app.run())

    await stopper_task, app_runner_task

    logger.debug("run_app() finished")


api_key = os.environ.get('VX_API_KEY')

if not api_key:
    config = configparser.ConfigParser()
    config.read('env.ini')
    api_key = config['visual.crossing']['vx_api_key']

wx_app = WeatherApp(zipcode='20895', api_key=api_key)
wx_app.set_matrix(matrix, options=options)
run_app(wx_app)
