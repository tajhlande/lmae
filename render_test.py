import logging

from PIL import ImageFont

import app_runner

from lmae_actor import Text, GradientRectangle
from lmae_animation import StraightMove, Sequence, Easing, HueRotate
from lmae_module import SingleStageRenderLoopAppModule

logging.basicConfig(level=logging.INFO, format='%(relativeCreated)9d %(name)10s [%(levelname)5s]: %(message)s')
logger = logging.getLogger("render_test")
logger.setLevel(logging.DEBUG)
print("LED Matrix Rendering Test")

# actor and animation setup

gradient_block = GradientRectangle(top_color=(128, 0, 0), bottom_color=(0, 0, 0))

gradient_hue_rotate = HueRotate(name="Gradient hue rotation", actor=gradient_block, duration=9.0, repeat=True,
                                initial_color=gradient_block.top_color,
                                callback=lambda rgb: gradient_block.set_top_color(rgb))

lmae_main_text = Text(name='LMAE main text', text="LMAE", position=(1, 1),
                      font=ImageFont.truetype("fonts/Roboto/Roboto-Thin.ttf", 24),
                      color=(255, 255, 255, 255), stroke_width=0)

lmae_shadow_text_1 = Text(name='LMAE shadow text 1', text="LMAE", position=(0, 2),
                          font=ImageFont.truetype("fonts/Roboto/Roboto-Thin.ttf", 24),
                          color=(0, 0, 255, 255), stroke_width=0)

lmae_shadow_text_1_hue_rotate = HueRotate(name="LMAE shadow text 1 hue rotation", actor=lmae_shadow_text_1,
                                          duration=9.0, repeat=True, initial_color=lmae_shadow_text_1.color,
                                          callback=lambda rgb: lmae_shadow_text_1.set_color(rgb))

lmae_shadow_text_2 = Text(name='LMAE shadow text 1', text="LMAE", position=(2, 2),
                          font=ImageFont.truetype("fonts/Roboto/Roboto-Thin.ttf", 24),
                          color=(0, 255, 0, 255), stroke_width=0)

lmae_shadow_text_2_hue_rotate = HueRotate(name="LMAE shadow text 2 hue rotation", actor=lmae_shadow_text_2,
                                          duration=9.0, repeat=True, initial_color=lmae_shadow_text_2.color,
                                          callback=lambda rgb: lmae_shadow_text_2.set_color(rgb))


lmae_long_1 = Text(name='LMAE long 1', text="LED Matrix Animation Engine", position=(0, 1),
                   font=ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5),
                   color=(255, 255, 255, 128), stroke_width=0)

ll_1_seq = Sequence(actor=lmae_long_1, repeat=True, animations=[
    StraightMove(actor=lmae_long_1, distance=(-43, 0), duration=3.0, easing=Easing.BEZIER),
    StraightMove(actor=lmae_long_1, distance=(43, 0), duration=3.0, easing=Easing.BEZIER),
])

lmae_long_2 = Text(name='LMAE long 1', text="LED Matrix Animation Engine", position=(-14, 9),
                   font=ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5),
                   color=(0, 0, 0, 255), stroke_width=0)

ll_2_seq = Sequence(actor=lmae_long_2, repeat=True, animations=[
    StraightMove(actor=lmae_long_2, distance=(-30, 0), duration=2.0, easing=Easing.LINEAR),
    StraightMove(actor=lmae_long_2, distance=(43, 0), duration=3.0, easing=Easing.LINEAR),
    StraightMove(actor=lmae_long_2, distance=(-13, 0), duration=1.0, easing=Easing.LINEAR),
])

lmae_long_3 = Text(name='LMAE long 1', text="LED Matrix Animation Engine", position=(-29, 18),
                   font=ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5),
                   color=(0, 0, 0, 255), stroke_width=0)

ll_3_seq = Sequence(actor=lmae_long_3, repeat=True, animations=[
    StraightMove(actor=lmae_long_3, distance=(-14, 0), duration=1.0, easing=Easing.LINEAR),
    StraightMove(actor=lmae_long_3, distance=(43, 0), duration=3.0, easing=Easing.LINEAR),
    StraightMove(actor=lmae_long_3, distance=(-29, 0), duration=2.0, easing=Easing.LINEAR),
])

lmae_long_4 = Text(name='LMAE long 1', text="LED Matrix Animation Engine", position=(-43, 26),
                   font=ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5),
                   color=(255, 255, 255, 128), stroke_width=0)

ll_4_seq = Sequence(actor=lmae_long_4, repeat=True, animations=[
    StraightMove(actor=lmae_long_4, distance=(43, 0), duration=3.0, easing=Easing.BACK),
    StraightMove(actor=lmae_long_4, distance=(-43, 0), duration=3.0, easing=Easing.BACK),
])

lmae_long_1.set_visible(False)
lmae_long_2.set_visible(False)
lmae_long_3.set_visible(False)
lmae_long_4.set_visible(False)

app_runner.app_setup()
sample_app = SingleStageRenderLoopAppModule()
sample_app.set_matrix(app_runner.matrix, options=app_runner.matrix_options)
sample_app.add_actors(gradient_block,
                      lmae_long_1, lmae_long_2, lmae_long_3, lmae_long_4,
                      lmae_shadow_text_1, lmae_shadow_text_2, lmae_main_text)
sample_app.add_animations(ll_1_seq, ll_2_seq, ll_3_seq, ll_4_seq,
                          gradient_hue_rotate, lmae_shadow_text_1_hue_rotate, lmae_shadow_text_2_hue_rotate)

app_runner.start_app(sample_app)
