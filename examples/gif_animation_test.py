import logging
import os.path

from lmae import app_runner
from lmae.app import SingleStageRenderLoopApp
from lmae.component import AnimatedImage

logging.basicConfig(level=logging.INFO, format='%(relativeCreated)9d %(name)10s [%(levelname)5s]: %(message)s')
logger = logging.getLogger("gif_animation_test")
logger.setLevel(logging.DEBUG)
print("LED Matrix Module Test - GIF App")

resource_path = os.path.dirname(__file__)
kirby_gif_image = AnimatedImage(name="Kirby Animated Image", position=(17, 6), repeat=True)
kirby_gif_image.set_from_file(os.path.join(resource_path, "images/kirby-walk-anim.gif"))
kirby_animations = kirby_gif_image.get_animations()


if __name__ == "__main__":
    sample_app = SingleStageRenderLoopApp()
    sample_app.add_actors(kirby_gif_image)
    sample_app.add_animations(*kirby_animations)

    app_runner.start_app(sample_app)
