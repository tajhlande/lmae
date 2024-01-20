#import same stuff as examples provided (specifically looked at sprite_animation_test.py)
import logging
from PIL import Image
import app_runner
from lmae.actor import StillImage, Text
from lmae.app import SingleStageRenderLoopApp

#Set up output and logging to Terminal
logging.basicConfig(level=logging.INFO, format='%(relativeCreated)9d %(name)10s [%(levelname)5s]: %(message)s')
logger = logging.getLogger("logo_display")
logger.setLevel(logging.DEBUG)

#Initial App Setup
app_runner.app_setup()
display_width = app_runner.matrix_options.cols
display_height = app_runner.matrix_options.rows

logger.debug(f"Team Logo Test - Size: {display_width} w x {display_height} h")

#scale the image to the board size
if display_width == 64 and display_height == 32:
    scale = 0.075 #scale factor for 64x32 board
elif display_width == 128 and display_height == 64:
    scale = 0.15  #scale factor for 128x64 board
else:
    scale = 1
img1 = Image.open("images/gb.png")# Read the input image png file
size1 = (int(scale * img1.size[0]), int(scale * img1.size[1]))
logger.debug(f"rescaling image from {img1.size} to {size1}")
scaled_img1 = img1.resize(size1)# Scale the image
scaled_img1.save('images/gb_scaled.png')# Save the scaled image as new png

#Open image as StillImage actor
awayTeamLogo = StillImage(position=(0,0), image=Image.open('images/gb_scaled.png').convert('RGBA'))

#Render and run the app
sample_app = SingleStageRenderLoopApp(size=(display_width,display_height))
sample_app.set_matrix(app_runner.matrix, options=app_runner.matrix_options)
sample_app.add_actors(awayTeamLogo)

app_runner.start_app(sample_app)