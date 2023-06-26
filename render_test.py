import logging
import time
from lmae.core import Stage, StillImage, parse_matrix_options_command_line
from PIL import Image
from rgbmatrix import RGBMatrix, RGBMatrixOptions

logging.basicConfig(level=logging.DEBUG)
options = parse_matrix_options_command_line()

matrix = RGBMatrix(options=options)
stage = Stage(matrix=matrix, matrix_options=options)

kirby = StillImage(name='Kirby', position=(20, 12), image=Image.open("images/kirby_22.png").convert('RGBA'))
trees = StillImage(name='Trees', image=Image.open("images/trees-composite.png").convert('RGBA'))
grass = StillImage(name='Grass', image=Image.open("images/grass.png").convert('RGBA'))
stage.actors.extend((trees, kirby, grass))

stage.render_frame()

print("Press CTRL-C to stop sample")
while True:
    time.sleep(1)
