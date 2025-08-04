import os
import sys

import asyncio
import logging
import configparser
from lmae.app import App
from lmae.core import parse_matrix_options_command_line

# hackity hackington to determine whether we're going to use virtual bindings or not
import platform
os_name = platform.system()
virtual_leds = False
if os_name == 'Linux':
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
else:  # Windows or Darwin aka macOS
    # from lmae.display
    from lmae.display import VirtualRGBMatrix as RGBMatrix, VirtualRGBMatrixOptions as RGBMatrixOptions
    virtual_leds = True

matrix: RGBMatrix
logger: logging.Logger
matrix_options: RGBMatrixOptions


def get_env_parameter(env_key: str = None, ini_header: str = None, ini_key: str = None, default=None,
                      local_env_config: configparser.ConfigParser = None):
    result = None
    if env_key:
        result = os.environ.get(env_key)
        if result:
            return result

    if not local_env_config:
        local_env_config = env_config

    if ini_header and ini_key:

        try:
            result = local_env_config[ini_header][ini_key]

        except:
            pass

    if result:
        return result

    if default:
        return default

    else:
        env_key_msg = f"set environment variable {env_key}" if env_key else ""
        ini_key_msg = f"set INI file header [{ini_header}] and variable {ini_key}" if ini_key else ""

        print(f"Unable to find environment parameter. You must do one of the following:")
        if env_key_msg:
            print(env_key_msg)

        if ini_key_msg:
            print(ini_key_msg)
        sys.exit(-1)


_app_setup_happened = False


def app_setup():
    global _app_setup_happened
    if not _app_setup_happened:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)12s [%(levelname)5s]: %(message)s')
        global logger
        logger = logging.getLogger("app_runner")
        logger.setLevel(logging.DEBUG)
        logger.info("App Runner logging setup")

        global matrix_options
        matrix_options = parse_matrix_options_command_line()
        global matrix
        if virtual_leds:
            logger.info("Initializing virtual LED matrix")
        else:
            logger.info("Initializing real LED matrix")
        matrix = RGBMatrix(options=matrix_options)
    _app_setup_happened = True


# borrowed from StackOverflow:
# https://stackoverflow.com/questions/58454190/python-async-waiting-for-stdin-input-while-doing-other-stuff
async def async_input(string: str) -> str:
    await asyncio.to_thread(sys.stdout.write, f'{string} ')
    return (await asyncio.to_thread(sys.stdin.readline)).rstrip('\n')


async def stop_app(app: App):
    logger.info("***** Press return to stop the app *****")
    await async_input('')
    logger.debug("Return pressed")
    app.stop()


async def run_app(app: App):
    logger.debug("run_app() called")
    app.prepare()

    logger.info("Creating stopper task")
    stopper_task = asyncio.create_task(stop_app(app))

    logger.info("Creating app runner task")
    app_runner_task = asyncio.create_task(app.run())

    await asyncio.gather(stopper_task, app_runner_task)

    logger.debug("run_app() finished")


def start_app(app: App):
    app_setup()
    app.set_matrix(matrix=matrix, options=matrix_options)
    asyncio.run(run_app(app))


env_config = configparser.ConfigParser()
env_config.read('env.ini')

