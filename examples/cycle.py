import asyncio
import sys
import logging
import time

from context import lmae
from lmae import app_runner
import advent_app
import weather_app
import world_clock

log = logging.getLogger(__file__)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)
log.addHandler(handler)


async def run_app_with_timeout(app, timeout=600):
    """Runs a given app within the same interpreter process for a specified timeout."""

    try:
        log.debug(f"Preparing app to run for {timeout} seconds")
        app.prepare()

        log.info("Creating app runner task")
        app_runner_task = asyncio.create_task(app.run())

        await asyncio.wait_for(app_runner_task, timeout=timeout)

        logger.debug("run_app() finished")
    except asyncio.TimeoutError:
        log.info(f"Time limit reached")
    except Exception:
        log.exception(f"Error executing {app.__class__.__name__}")
        return

    if app.running:
        log.info(f"Stopping app {app.__class__.__name__}")
        app.stop()
    else:
        log.info(f"App {app.__class__.__name__} already stopped")


def run_apps_in_cycle(app_list, cycle_timeout=600):
    """Runs scripts in a cycle, each for 'cycle_timeout' seconds."""
    while True:
        for app in app_list:
            log.info(f"Starting app: {app.__class__.__name__}")
            asyncio.run(run_app_with_timeout(app, timeout=cycle_timeout))
            log.info(f"Finished or terminated app: {app.__class__.__name__}")
            time.sleep(1)  # Short pause between scripts


def create_apps_list():
    return [
        weather_app.WeatherApp.get_app_instance(),
        world_clock.WorldClock.get_app_instance(),
        # advent_app.AdventApp.get_app_instance()
    ]


if __name__ == "__main__":
    import gc
    gc.set_debug(gc.DEBUG_LEAK)
    apps = create_apps_list()
    app_runner.app_setup()
    for app in apps:
        app.set_matrix(matrix=app_runner.matrix, options=app_runner.matrix_options)
    run_apps_in_cycle(apps, cycle_timeout=5)
