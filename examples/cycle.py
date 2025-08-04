import asyncio
import sys
import logging
import time
import subprocess
import os.path
from importlib.util import spec_from_file_location, module_from_spec

from context import lmae
from lmae import app_runner
import advent_app
import weather_app
import world_clock

# debugging tool imports
import tracemalloc, time
import psutil, os, time
import threading

from lmae.app import App

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)12s [%(levelname)5s]: %(message)s')
log = logging.getLogger("cycle.py")
# handler = logging.StreamHandler(sys.stdout)
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# handler.setLevel(logging.DEBUG)
# log.handlers.clear()
# log.addHandler(handler)
log.setLevel(logging.INFO)

async def run_app_with_timeout(app, timeout=600):
    """Runs a given app within the same interpreter process for a specified timeout."""

    try:
        log.debug(f"Preparing app to run for {timeout} seconds")
        app.prepare()

        log.debug("Creating app runner task")
        app_runner_task = asyncio.create_task(app.run())

        await asyncio.wait_for(app_runner_task, timeout=timeout)

        log.debug("run_app() finished")
    except asyncio.TimeoutError:
        log.debug(f"Time limit reached")
    except Exception:
        log.exception(f"Error executing {app.__class__.__name__}")
        return

    if app.running:
        log.debug(f"Stopping app {app.__class__.__name__}")
        app.stop()
    else:
        log.debug(f"App {app.__class__.__name__} already stopped")


async def run_app_as_subprocess_with_timeout(python_path: str, app_script_path: str, timeout=600):
    """Runs a given app as a subprocess for a specified timeout."""

    try:
        log.debug(f"Executing app subprocess to run for {timeout} seconds")

        subprocess.run(args=[python_path, app_script_path], timeout=timeout, check=True)
        #app_runner_task = asyncio.create_task()

        #await asyncio.wait_for(app_runner_task, timeout=timeout)

        log.debug(f"App finished")
    except (asyncio.TimeoutError, subprocess.TimeoutExpired):
        log.debug(f"Time limit reached")
    except Exception:
        log.exception(f"Error executing {app.__class__.__name__}")
        return

    if app.running:
        log.debug(f"Stopping app {app.__class__.__name__}")
        app.stop()
    else:
        log.info(f"App {app.__class__.__name__} already stopped")


def run_apps_in_cycle(app_list, cycle_timeout=600):
    """Runs scripts in a cycle, each for 'cycle_timeout' seconds."""
    last_time : float = None
    tracemalloc.start()
    proc = psutil.Process(os.getpid())
    while True:
        for app in app_list:
            log.info(f"Starting app: {app.__class__.__name__}")
            asyncio.run(run_app_with_timeout(app, timeout=cycle_timeout))
            log.info(f"Finished or terminated app: {app.__class__.__name__}")
            gc.collect()
            # graph = refcycle.objects_reachable_from(app_list[0])
            # log.warning(f"Graph size for Weather app: {len(graph)}")
            time.sleep(1)  # Short pause between scripts
            now_time = time.time()
            if not last_time or now_time > last_time + 5 * 60:
                last_time = now_time
                snapshot = tracemalloc.take_snapshot()
                top = snapshot.statistics('lineno')
                log.info("Top memory lines:")
                for stat in top[:5]:
                    log.info(f"    {stat}")
                # log.info(f"Memory: {proc.memory_info().rss / 1024**2:.1f} MB")
                log.info(f"Process memory info: {proc.memory_info()}")


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
        advent_app.AdventApp.get_app_instance(),
        world_clock.WorldClock.get_app_instance(),
        weather_app.WeatherApp.get_app_instance()
    ]

def load_app_instance(module_path: str, module_name: str, app_class_name: str) -> App:
    if module_name in sys.modules.keys():
        log.info(f"Module {module_name} already loaded")
        module = sys.modules[module_name]
    else:
        log.info(f"Creating spec for module {module_name} at path {module_path}")
        try:
            spec = spec_from_file_location(module_name, module_path)
        except ImportError:
            raise RuntimeError(f"Unable to load spec for module {module_name} at path {module_path}")

        log.info(f"Loading module {module_name}")
        try:
            module = module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except FileNotFoundError | ImportError:
            raise RuntimeError(f"Unable to load module {module_name} at path {module_path}")

    log.info(f"Instantiating app class {app_class_name} from module {module_name}")
    try:
        app_class: App = getattr(module, app_class_name)
        app = app_class.get_app_instance()
        return app
    except NameError | OSError:
        raise RuntimeError(f"Unable to instantiate app class {app_class_name} in module {module_name}")


def create_apps_list_from_app_names():
    module_base_path = os.path.dirname(os.path.realpath(__file__))
    log.info(f"Module base path: {module_base_path}")
    app_config_list = [
        {
            'module_name': 'lmae.examples.advent_app',
            'module_path': 'advent_app.py',
            'app_class': 'AdventApp'
        },
        {
            'module_name': 'lmae.examples.weather_app',
            'module_path': 'weather_app.py',
            'app_class': 'WeatherApp'
        },
        {
            'module_name': 'lmae.examples.world_clock',
            'module_path': 'world_clock.py',
            'app_class': 'WorldClock'
        }
    ]

    return map(lambda config: load_app_instance(os.path.join(module_base_path, config['module_path']),
                                                config['module_name'], config['app_class']),
               app_config_list)


if __name__ == "__main__":
    import gc
    #gc.set_debug(gc.DEBUG_LEAK)
    apps = create_apps_list() #create_apps_list_from_app_names()
    log.info(f"Setting up app runner and initializing LED matrix")
    app_runner.app_setup()
    for app in apps:
        app.set_matrix(matrix=app_runner.matrix, options=app_runner.matrix_options)
    log.info(f"Beginning app execution")
    run_apps_in_cycle(apps, cycle_timeout=5)
    #run_apps_in_subprocess_cycle(["advent_app.py", "world_clock.py"], cycle_timeout=5)
