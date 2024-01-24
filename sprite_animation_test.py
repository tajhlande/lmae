import logging

from PIL import ImageFont

import app_runner
from lmae.actor import SpriteImage, Text
from lmae.app import SingleStageRenderLoopApp
from lmae.component import AnimatedSprite


logging.basicConfig(level=logging.INFO, format='%(relativeCreated)9d %(name)10s [%(levelname)5s]: %(message)s')
logger = logging.getLogger("sprite_anim_test")
logger.setLevel(logging.DEBUG)
print("LED Matrix Module Test - Sprite Animation Test")

# set up stage
logger.debug("Setting up stage")

mario_sprite = SpriteImage(name="Mario Sprite", position=(35, 0))
mario_sprite.set_from_file("images/smb/smb2_heroes_sheet.png",  # "images/smb/smb_mario_sheet.png",
                           "images/smb/smb2_mario_sprites.json")  # "images/smb/mario-sprites.json")
mario_sprite.set_sprite("sprite1")

mario_animation = AnimatedSprite(name="Mario Animated", position=mario_sprite.position,
                                 sprite=mario_sprite, frames=list(mario_sprite.spec.keys()),
                                 duration=len(mario_sprite.spec.keys()) / 4.0, repeat=True)

font = ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5)

sprite_label = Text(name="Sprite label", position=(2, 24), font=font, stroke_width=1)


def set_mario_sprite_frame_name():
    sprite_label.set_text(mario_sprite.selected)


sample_app = SingleStageRenderLoopApp()
sample_app.add_actors(mario_animation, sprite_label)
sample_app.add_animations(*mario_animation.get_animations())
sample_app.set_pre_render_callback(set_mario_sprite_frame_name)

app_runner.start_app(sample_app)
