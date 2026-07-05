import logging
import os.path

from PIL import Image, ImageFont
from pilmoji.source import AppleEmojiSource

import lmae.app_runner as app_runner
from lmae.actor import EmojiText, StillImage, Text
from lmae.animation import Hide, Sequence, Show, StraightMove
from lmae.app import SingleStageRenderLoopApp

logging.basicConfig(
    level=logging.INFO,
    format="%(relativeCreated)9d %(name)10s [%(levelname)5s]: %(message)s",
)
logger = logging.getLogger("actor_test")
logger.setLevel(logging.DEBUG)
print("Actors Test")

resource_path = os.path.dirname(__file__)

kirby_image_path = os.path.join(resource_path, "images/kirby_22.png")
kirby = StillImage(
    name="Kirby", position=(-22, 12), image=Image.open(kirby_image_path).convert("RGBA")
)

kirby_movement = StraightMove(name="Moving Kirby", actor=kirby, duration=2.0, distance=(86, 0))
kirby_hide = Hide(actor=kirby)
kirby_reset = StraightMove(name="Reset Kirby", actor=kirby, duration=0.1, distance=(-86, 0))
kirby_show = Show(actor=kirby)
kirby_sequence = Sequence(
    name="Kirby Sequence",
    actor=kirby,
    repeat=True,
    animations=[kirby_movement, kirby_hide, kirby_reset, kirby_show],
)

trees_image_path = os.path.join(resource_path, "images/trees-composite.png")
trees = StillImage(name="Trees", image=Image.open(trees_image_path).convert("RGBA"))
grass_image_path = os.path.join(resource_path, "images/grass.png")
grass = StillImage(name="Grass", image=Image.open(grass_image_path).convert("RGBA"))
font_path = os.path.join(resource_path, "fonts/et-bt6001-font/EtBt6001-JO47.ttf")
words = Text(
    name="Text",
    text="Hello,\nworld!",
    position=(5, 5),
    # the following are the fonts native point sizes to avoid blurring
    font=ImageFont.truetype(font_path, 6),  # good option for fitting a lot
    color=(255, 255, 255, 255),
    stroke_color=(0, 0, 0, 255),
    stroke_width=1,
)
emoji_font_path = os.path.join(resource_path, "fonts/et-bt6001-font/EtBt6001-JO47.ttf")
emoji_words = EmojiText(
    name="EmojiText",
    text="☀️🌤️⛈️🌗",
    position=(1, 1),
    text_font=ImageFont.truetype(emoji_font_path, 20),
    emoji_source=AppleEmojiSource,
    color=(255, 255, 255, 255),
    stroke_color=(0, 0, 0, 255),
    stroke_width=1,
)

if __name__ == "__main__":
    sample_app = SingleStageRenderLoopApp()
    sample_app.add_actors(trees, emoji_words, words, kirby, grass)
    sample_app.add_animations(kirby_sequence)

    app_runner.start_app(sample_app)
