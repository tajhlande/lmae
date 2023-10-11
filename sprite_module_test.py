import logging

from PIL import ImageFont

import app_runner
from lmae.actor import SpriteImage, Text
from lmae.app import SingleStageRenderLoopApp

logging.basicConfig(level=logging.INFO, format='%(relativeCreated)9d %(name)10s [%(levelname)5s]: %(message)s')
logger = logging.getLogger("app_module_test")
logger.setLevel(logging.DEBUG)
print("LED Matrix Module Test - Sprite App")

# options: RGBMatrixOptions = parse_matrix_options_command_line()
#logger.info("Initializing matrix")
# matrix = RGBMatrix(options=options)


# set up stage
logger.debug("Setting up stage")


def kirby_movement(frame_number: int) -> tuple[int, int]:
    return frame_number % 86 - 22, 12


# weather_sprite = SpriteImage(name='Weather Condition', position=(int((64-17)/2), int((32-17)/2)))
# weather_sprite.set_from_file("images/weather-sprites.png", "images/weather-sprites.json")
# weather_sprite.set_sprite("sunny")

mario_sprite = SpriteImage(name="Mario Sprite", position=(35, 0))
mario_sprite.set_from_file("images/smb/smb2_heroes_sheet.png",  # "images/smb/smb_mario_sheet.png",
                           "images/smb/smb2_mario_sprites.json")  # "images/smb/mario-sprites.json")
mario_sprite.set_sprite("sprite1")

font = ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5)

sprite_label = Text(name="Sprite label", position=(2, 24), font=font, stroke_width=1)

# def set_weather_sprite_frame(frame: int):
#     frame_offset = frame % 1600
#     frame_index = int(frame_offset / 100)
#     weather_sprite.set_sprite(list(weather_sprite.spec.keys())[frame_index])


sprite_frame = 0


def set_mario_sprite_frame():
    global sprite_frame
    # frame_offset = sprite_frame % 160
    frame_index = int((sprite_frame / 20) % len(mario_sprite.spec))
    selected_sprite = list(mario_sprite.spec.keys())[frame_index]
    mario_sprite.set_sprite(selected_sprite)
    # logger.debug(f"current frame: {sprite_frame}, index: {frame_index}, selected sprite: {mario_sprite.selected}")
    sprite_frame += 1

    mario_sprite.set_position((35, 31 - mario_sprite.size[1]))
    sprite_label.set_text(selected_sprite)


# def stop_app(app: AppModule):
#     logger.info("***** Press return to stop the app *****")
#     input()
#     logger.debug("Return pressed")
#     app.stop()
#
#
# def run_app(app: AppModule):
#     logger.debug("run_app() called")
#     app.prepare()
#
#     logger.info("Starting stopper thread")
#     stopper_thread = Thread(target=stop_app, args=[app])
#     stopper_thread.start()
#
#     logger.info("Running app")
#     app_thread = Thread(target=app.run)
#     app_thread.start()
#
#     stopper_thread.join()
#     app_thread.join()
#
#     logger.debug("run_app() finished")


app_runner.app_setup()
sample_app = SingleStageRenderLoopApp()
sample_app.set_matrix(app_runner.matrix, options=app_runner.matrix_options)
sample_app.add_actors(mario_sprite, sprite_label)
sample_app.set_pre_render_callback(set_mario_sprite_frame)

app_runner.start_app(sample_app)

