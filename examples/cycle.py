import asyncio
import pwd
import sys
import logging
import time
import subprocess
import os.path
from subprocess import STDOUT

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

        log.debug("run_app() finished")
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


async def run_app_as_subprocess_with_timeout(python_path: str, app_script_path: str, timeout=600):
    """Runs a given app as a subprocess for a specified timeout."""

    try:
        log.info(f"Executing app subprocess to run for {timeout} seconds")
        log.info(f"exec: sudo {python_path} {app_script_path}")
        log.info(f"Parent process user: {os.geteuid()} ({os.getlogin()})")

        #process = subprocess.run(args=["sudo", python_path, app_script_path], check=True)
        process = subprocess.Popen(args=["/usr/bin/sudo", python_path, app_script_path],
                                   stdout=sys.stdout, stderr=sys.stderr, user=os.getlogin())


        #app_runner_task = asyncio.create_task()

        #await asyncio.wait_for(app_runner_task, timeout=timeout)

        log.debug(f"App finished")
    except asyncio.TimeoutError:
        log.info(f"Time limit reached")
    except Exception:
        log.exception(f"Error executing {app_script_path}")
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
            # gc.collect()
            # graph = refcycle.objects_reachable_from(app_list[0])
            # log.warning(f"Graph size for Weather app: {len(graph)}")
            time.sleep(1)  # Short pause between scripts

def run_apps_in_subprocess_cycle(app_script_list: list[str], cycle_timeout=600):
    """Runs scripts in a cycle, each for 'cycle_timeout' seconds."""
    python_path = sys.executable
    current_script_path = os.path.dirname(os.path.realpath(__file__))
    log.info(f"Python path: {python_path}")
    log.info(f"Current script path: {current_script_path}")
    while True:
        for app_script in app_script_list:
            app_script_path = os.path.join(current_script_path, app_script)
            log.info(f"Starting app {app_script} from file {app_script_path}")
            asyncio.run(run_app_as_subprocess_with_timeout(python_path, app_script_path, timeout=cycle_timeout))
            log.info(f"Finished or terminated app: {app_script}")
            time.sleep(1)  # Short pause between scripts


def create_apps_list():
    return [
        weather_app.WeatherApp.get_app_instance(),
        world_clock.WorldClock.get_app_instance(),
        # advent_app.AdventApp.get_app_instance()
    ]


if __name__ == "__main__":
    import gc
    # gc.set_debug(gc.DEBUG_LEAK)
    apps = create_apps_list()
    app_runner.app_setup()
    for app in apps:
        app.set_matrix(matrix=app_runner.matrix, options=app_runner.matrix_options)
    run_apps_in_subprocess_cycle(["weather_app.py", "world_clock.py"], cycle_timeout=15)
