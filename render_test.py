import logging

from PIL import ImageFont

import app_runner
from lmae.actor import Text, GradientRectangle
from lmae.animation import StraightMove, Sequence, Easing, HueRotate
from lmae.app import SingleStageRenderLoopApp

logging.basicConfig(level=logging.INFO, format='%(relativeCreated)9d %(name)10s [%(levelname)5s]: %(message)s')
logger = logging.getLogger("render_test")
logger.setLevel(logging.DEBUG)
print("LED Matrix Rendering Test")

# initial app setup
app_runner.app_setup()
display_width = app_runner.matrix_options.cols
display_height = app_runner.matrix_options.rows
app_runner.logger.debug(f"Display dimensions: {display_width} w x {display_height} h")

# actor and animation setup
gradient_block = GradientRectangle(size=(display_width - 1, display_height - 1),
                                   top_color=(128, 0, 0), bottom_color=(0, 0, 0))

gradient_hue_rotate = HueRotate(name="Gradient hue rotation", actor=gradient_block, duration=9.0, repeat=True,
                                initial_color=gradient_block.top_color,
                                callback=lambda rgb: gradient_block.set_top_color(rgb))

lmae_main_text = Text(name='LMAE main text', text="LMAE",
                      position=(int(1 + (display_width - 64) / 2), int(1 + (display_height - 32) / 2)),
                      font=ImageFont.truetype("fonts/Roboto/Roboto-Thin.ttf", 24),
                      color=(255, 255, 255, 255), stroke_width=0)

lmae_shadow_text_1 = Text(name='LMAE shadow text 1', text="LMAE",
                          position=(int(0 + (display_width - 64) / 2), int(2 + (display_height - 32) / 2)),
                          font=ImageFont.truetype("fonts/Roboto/Roboto-Thin.ttf", 24),
                          color=(0, 0, 255, 255), stroke_width=0)

lmae_shadow_text_1_hue_rotate = HueRotate(name="LMAE shadow text 1 hue rotation", actor=lmae_shadow_text_1,
                                          duration=9.0, repeat=True, initial_color=lmae_shadow_text_1.color,
                                          callback=lambda rgb: lmae_shadow_text_1.set_color(rgb))

lmae_shadow_text_2 = Text(name='LMAE shadow text 2', text="LMAE",
                          position=(int(2 + (display_width - 64) / 2), int(2 + (display_height - 32) / 2)),
                          font=ImageFont.truetype("fonts/Roboto/Roboto-Thin.ttf", 24),
                          color=(0, 255, 0, 255), stroke_width=0)

lmae_shadow_text_2_hue_rotate = HueRotate(name="LMAE shadow text 2 hue rotation", actor=lmae_shadow_text_2,
                                          duration=9.0, repeat=True, initial_color=lmae_shadow_text_2.color,
                                          callback=lambda rgb: lmae_shadow_text_2.set_color(rgb))


lmae_long_1 = Text(name='LMAE long 1', text="LED Matrix Animation Engine",
                   position=(int(0 + (display_width - 64) / 2), 1),
                   font=ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5),
                   color=(255, 255, 255, 128), stroke_width=0)

ll_1_seq = Sequence(actor=lmae_long_1, repeat=True, animations=[
    StraightMove(actor=lmae_long_1, distance=(-43 + 64 - display_width, 0), duration=3.0, easing=Easing.BEZIER),
    StraightMove(actor=lmae_long_1, distance=(43 - 64 + display_width, 0), duration=3.0, easing=Easing.BEZIER),
])

lmae_long_2 = Text(name='LMAE long 1', text="LED Matrix Animation Engine",
                   position=(int(-14 + (display_width - 64) / 2), 9),
                   font=ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5),
                   color=(0, 0, 0, 255), stroke_width=0)

ll_2_seq = Sequence(actor=lmae_long_2, repeat=True, animations=[
    StraightMove(actor=lmae_long_2, distance=(-30, 0), duration=2.0, easing=Easing.LINEAR),
    StraightMove(actor=lmae_long_2, distance=(43, 0), duration=3.0, easing=Easing.LINEAR),
    StraightMove(actor=lmae_long_2, distance=(-13, 0), duration=1.0, easing=Easing.LINEAR),
])

lmae_long_3 = Text(name='LMAE long 1', text="LED Matrix Animation Engine",
                   position=(int(-29 + (display_width - 64) / 2), 18 + display_height - 32),
                   font=ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5),
                   color=(0, 0, 0, 255), stroke_width=0)

ll_3_seq = Sequence(actor=lmae_long_3, repeat=True, animations=[
    StraightMove(actor=lmae_long_3, distance=(-14, 0), duration=1.0, easing=Easing.LINEAR),
    StraightMove(actor=lmae_long_3, distance=(43, 0), duration=3.0, easing=Easing.LINEAR),
    StraightMove(actor=lmae_long_3, distance=(-29, 0), duration=2.0, easing=Easing.LINEAR),
])

lmae_long_4 = Text(name='LMAE long 1', text="LED Matrix Animation Engine", position=(-43, 26 + display_height - 32),
                   font=ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5),
                   color=(255, 255, 255, 128), stroke_width=0)

ll_4_seq = Sequence(actor=lmae_long_4, repeat=True, animations=[
    StraightMove(actor=lmae_long_4, distance=(43, 0), duration=3.0, easing=Easing.BACK),
    StraightMove(actor=lmae_long_4, distance=(-43, 0), duration=3.0, easing=Easing.BACK),
])

sample_app = SingleStageRenderLoopApp(size=(display_width, display_height))
sample_app.set_matrix(app_runner.matrix, options=app_runner.matrix_options)

sample_app.add_actors(gradient_block,
                      lmae_long_1, lmae_long_2, lmae_long_3, lmae_long_4,
                      lmae_shadow_text_1, lmae_shadow_text_2, lmae_main_text)
sample_app.add_animations(ll_1_seq, ll_2_seq, ll_3_seq, ll_4_seq,
                          gradient_hue_rotate, lmae_shadow_text_1_hue_rotate, lmae_shadow_text_2_hue_rotate)

app_runner.start_app(sample_app)
