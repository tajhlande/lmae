from colorsys import rgb_to_hsv, hsv_to_rgb
import logging
from typing import Union, Callable

from PIL import Image, ImageFont


from lmae_core import _get_sequential_name, Canvas
from lmae_actor import Actor, Text, EmojiText
from lmae_animation import Animation, Hide, Show, StraightMove, Sequence, Easing
from lmae_module import SingleStageRenderLoopAppModule
import app_runner

logging.basicConfig(level=logging.INFO, format='%(relativeCreated)9d %(name)10s [%(levelname)5s]: %(message)s')
logger = logging.getLogger("render_test")
logger.setLevel(logging.DEBUG)
print("LED Matrix Rendering Test")


class GradientRectangle(Actor):
    """
    A filled rectangle drin a gradient shaded from top to bottom
    """
    def __init__(self, name: str = None, position: tuple[int, int] = (0, 0), size: tuple[int, int] = (63, 31),
                 top_color: Union[tuple[int, int, int], tuple[int, int, int, int]] = (255, 255, 255, 255),
                 bottom_color: Union[tuple[int, int, int], tuple[int, int, int, int]] = (0, 0, 0, 0)):
        name = name or _get_sequential_name("GradientRectangle")
        super().__init__(name, position)
        self.size = size
        self.top_color = top_color
        self.bottom_color = bottom_color

    def set_top_color(self, new_color: Union[tuple[int, int, int], tuple[int, int, int, int]]):
        if self.top_color != new_color:
            self.changes_since_last_render = True
        self.top_color = new_color

    def set_bottom_color(self, new_color: Union[tuple[int, int, int], tuple[int, int, int, int]]):
        if self.bottom_color != new_color:
            self.changes_since_last_render = True
        self.bottom_color = new_color

    def render(self, canvas: Canvas):
        draw = canvas.image_draw
        y_start = self.position[1]
        y_end = self.position[1] + self.size[1]
        x_start = self.position[0]
        x_end = self.position[0] + self.size[0]

        for y in range(y_start, y_end):
            gradient_factor = 1 - (y * 1.0 / self.size[1])
            color = self.interpolate_color(self.top_color, self.bottom_color, gradient_factor)
            draw.line((x_start, y, x_end, y), fill=color, width=1)

        self.changes_since_last_render = False

    @staticmethod
    def interpolate_color(start_color: Union[tuple[int, int, int], tuple[int, int, int, int]],
                          end_color: Union[tuple[int, int, int], tuple[int, int, int, int]],
                          blend_factor: float) -> tuple[int, int, int, int]:
        inv_blend_factor = 1.0 - blend_factor
        blend_red = int(start_color[0] * blend_factor + end_color[0] * inv_blend_factor)
        blend_green = int(start_color[1] * blend_factor + end_color[1] * inv_blend_factor)
        blend_blue = int(start_color[2] * blend_factor + end_color[2] * inv_blend_factor)
        start_alpha = start_color[3] if len(start_color) == 4 else 255
        end_alpha = end_color[3] if len(end_color) == 4 else 255
        blend_alpha = int(start_alpha * blend_factor + end_alpha * inv_blend_factor)
        return blend_red, blend_green, blend_blue, blend_alpha


class HueRotate(Animation):
    def __init__(self, name: str = None, actor: Actor = None, initial_color: tuple[int, int, int] = (255, 255, 255),
                 duration: float = 10.0, callback: Callable[[tuple[int, int, int]], None] = None,
                 repeat: bool = False):
        name = name or _get_sequential_name("HueRotate")
        super().__init__(name=name, actor=actor, duration=duration, repeat=repeat)
        self.logger.debug(f"Repeat: {self.repeat}")
        self.initial_hsv = rgb_to_hsv(initial_color[0] / 255.0, initial_color[1] / 255.0, initial_color[2] / 255.0)
        self.color_set_callback: Callable[[tuple[int, int, int]], None] = callback

    def is_finished(self) -> bool:
        return self.get_simulated_time() > self.duration

    def update_actor(self, current_time: float):
        #  all times relative to start
        elapsed_time = self.get_elapsed_time(current_time)
        action_time = elapsed_time
        if elapsed_time > self.duration:
            action_time = self.duration
        duration_fraction = 0.0 if self.duration == 0 else action_time / self.duration

        adjusted_hue = self.initial_hsv[0] + duration_fraction
        while adjusted_hue >= 1.0:
            adjusted_hue = adjusted_hue - 1.0

        float_rgb_color = hsv_to_rgb(adjusted_hue, self.initial_hsv[1], self.initial_hsv[2])
        rgb_color = round(float_rgb_color[0] * 255), round(float_rgb_color[1] * 255), round(float_rgb_color[2] * 255)
        self.color_set_callback(rgb_color)
        self.set_update_time(current_time)


# actor and animation setup

gradient_block = GradientRectangle(top_color=(128, 0, 0), bottom_color=(0, 0, 0))

gradient_hue_rotate = HueRotate(name="Gradient hue rotation", actor=gradient_block, duration=9.0, repeat=True,
                                initial_color=gradient_block.top_color,
                                callback=lambda rgb: gradient_block.set_top_color(rgb))

lmae_main_text = Text(name='LMAE main text', text="LMAE", position=(0, 0),
                      font=ImageFont.truetype("fonts/Roboto/Roboto-Thin.ttf", 24),
                      color=(255, 255, 255, 255), stroke_width=0)

lmae_shadow_text_1 = Text(name='LMAE shadow text 1', text="LMAE", position=(-1, 1),
                          font=ImageFont.truetype("fonts/Roboto/Roboto-Thin.ttf", 24),
                          color=(0, 0, 255, 255), stroke_width=0)

lmae_shadow_text_1_hue_rotate = HueRotate(name="LMAE shadow text 1 hue rotation", actor=lmae_shadow_text_1,
                                          duration=9.0, repeat=True, initial_color=lmae_shadow_text_1.color,
                                          callback=lambda rgb: lmae_shadow_text_1.set_color(rgb))

lmae_shadow_text_2 = Text(name='LMAE shadow text 1', text="LMAE", position=(1, 1),
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
                   color=(0, 0, 0, 0), stroke_width=0)

ll_2_seq = Sequence(actor=lmae_long_2, repeat=True, animations=[
    StraightMove(actor=lmae_long_2, distance=(-30, 0), duration=2.0, easing=Easing.LINEAR),
    StraightMove(actor=lmae_long_2, distance=(43, 0), duration=3.0, easing=Easing.LINEAR),
    StraightMove(actor=lmae_long_2, distance=(-13, 0), duration=1.0, easing=Easing.LINEAR),
])

lmae_long_3 = Text(name='LMAE long 1', text="LED Matrix Animation Engine", position=(-29, 17),
                   font=ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5),
                   color=(0, 0, 0, 0), stroke_width=0)

ll_3_seq = Sequence(actor=lmae_long_3, repeat=True, animations=[
    StraightMove(actor=lmae_long_3, distance=(-14, 0), duration=1.0, easing=Easing.LINEAR),
    StraightMove(actor=lmae_long_3, distance=(43, 0), duration=3.0, easing=Easing.LINEAR),
    StraightMove(actor=lmae_long_3, distance=(-29, 0), duration=2.0, easing=Easing.LINEAR),
])

lmae_long_4 = Text(name='LMAE long 1', text="LED Matrix Animation Engine", position=(-43, 25),
                   font=ImageFont.truetype("fonts/teeny-tiny-pixls-font/TeenyTinyPixls-o2zo.ttf", 5),
                   color=(255, 255, 255, 128), stroke_width=0)

ll_4_seq = Sequence(actor=lmae_long_4, repeat=True, animations=[
    StraightMove(actor=lmae_long_4, distance=(43, 0), duration=3.0, easing=Easing.BACK),
    StraightMove(actor=lmae_long_4, distance=(-43, 0), duration=3.0, easing=Easing.BACK),
])


app_runner.app_setup()
sample_app = SingleStageRenderLoopAppModule()
sample_app.set_matrix(app_runner.matrix, options=app_runner.matrix_options)
sample_app.add_actors(gradient_block,
                      lmae_long_1, lmae_long_2, lmae_long_3, lmae_long_4,
                      lmae_shadow_text_1, lmae_shadow_text_2, lmae_main_text)
sample_app.add_animations(ll_1_seq, ll_2_seq, ll_3_seq, ll_4_seq,
                          gradient_hue_rotate, lmae_shadow_text_1_hue_rotate, lmae_shadow_text_2_hue_rotate)

app_runner.start_app(sample_app)

