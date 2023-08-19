from lmae_module import AppModule
from threading import Thread
import logging
import os
import configparser
from lmae_core import parse_matrix_options_command_line
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from weather_app import WeatherApp

logging.basicConfig(level=logging.INFO, format='%(relativeCreated)9d %(name)10s [%(levelname)5s]: %(message)s')
logger = logging.getLogger("app_runner")
logger.setLevel(logging.DEBUG)
print("App Runner")

options: RGBMatrixOptions = parse_matrix_options_command_line()
logger.info("Initializing matrix")
matrix = RGBMatrix(options=options)


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


api_key = os.environ.get('VX_API_KEY')

if not api_key:
    config = configparser.ConfigParser()
    config.read('env.ini')
    api_key = config['visual.crossing']['vx_api_key']

wx_app = WeatherApp(zipcode='20895', api_key=api_key)
wx_app.set_matrix(matrix, options=options)
run_app(wx_app)
