#!/usr/bin/env python
import time
import sys
import logging

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image

logging.basicConfig(level=logging.DEBUG)

if len(sys.argv) < 2:
    sys.exit("Require an image argument")
else:
    image_file = sys.argv[1]

image = Image.open(image_file)
logging.info(f"Image dimensions: {image.width} x {image.height}")

# Configuration for the matrix
options = RGBMatrixOptions()
options.rows = 32
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'regular'  # If you have an Adafruit HAT: 'adafruit-hat'

logging.debug("Creating matrix object")
matrix = RGBMatrix(options = options)

# Make image fit our screen.
logging.debug("Creating thumbnail of image")
image.thumbnail((matrix.width, matrix.height), Image.ANTIALIAS)
logging.debug(f"Image dimensions now: {image.width} x {image.height}")

logging.debug("Converting image to RGB")
rgbImage = image.convert('RGB')

logging.debug("Getting pixel values at 0,0, 5,5, 10,10")
logging.debug(f"(0,0)   = {rgbImage.getpixel((0,0))}") 
logging.debug(f"(5,5)   = {rgbImage.getpixel((5,5))}")
logging.debug(f"(10,10) = {rgbImage.getpixel((10,10))}")


matrix.SetImage(rgbImage, 0, 0)

matrix.SetPixel(0, 0, rgbImage.getpixel((0,0))[0], rgbImage.getpixel((0,0))[1], rgbImage.getpixel((0,0))[2]);
matrix.Fill(255, 255, 255)

try:
    print("Press CTRL-C to stop.")
    while True:
        time.sleep(100)
except KeyboardInterrupt:
    sys.exit(0)
