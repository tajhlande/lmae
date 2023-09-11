import sys

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

config = configparser.ConfigParser()
config.read('env.ini')

# Visual Crossing
# api_key = os.environ.get('VX_API_KEY')

# OpenWeather
api_key = os.environ.get('OW_API_KEY')

if not api_key:
    # VX
    # api_key = config['visual.crossing']['vx_api_key']

    # OpenWeather
    api_key = config['openweather']['ow_api_key']

latitude = os.environ.get('LATITUDE')
if not latitude:
    latitude = config['location']['latitude']

longitude = os.environ.get('LONGITUDE')
if not longitude:
    longitude = config['location']['longitude']

wx_app = WeatherApp(api_key=api_key, latitude=latitude, longitude=longitude)
wx_app.set_matrix(matrix, options=options)
asyncio.run(run_app(wx_app))
