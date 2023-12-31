import logging

import app_runner
from lmae.app import SingleStageRenderLoopApp
from lmae.component import AnimatedImage

logging.basicConfig(level=logging.INFO, format='%(relativeCreated)9d %(name)10s [%(levelname)5s]: %(message)s')
logger = logging.getLogger("gif_animation_test")
logger.setLevel(logging.DEBUG)
print("LED Matrix Module Test - GIF App")

kirby_gif_image = AnimatedImage(name="Kirby Animated Image", position=(17, 6), repeat=True)
kirby_gif_image.set_from_file("images/kirby-walk-anim.gif")
kirby_animations = kirby_gif_image.get_animations()


app_runner.app_setup()
sample_app = SingleStageRenderLoopApp()
sample_app.set_matrix(app_runner.matrix, options=app_runner.matrix_options)
sample_app.add_actors(kirby_gif_image)
sample_app.add_animations(*kirby_animations)

app_runner.start_app(sample_app)
