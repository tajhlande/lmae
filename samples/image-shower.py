#!/usr/bin/env python
import logging
import math
import time
from samplebase import SampleBase
from PIL import Image

logging.basicConfig(level=logging.DEBUG)


class ImageShower(SampleBase):
    def __init__(self, *args, **kwargs):
        super(ImageShower, self).__init__(*args, **kwargs)
        self.parser.add_argument("-i", "--image", help="The image to display",
                                 default="../../../examples-api-use/runtext.ppm")

    def run(self):
        logging.debug(f"Opening image file: {self.args.image}")
        image = Image.open(self.args.image).convert('RGB')

        if image.width > self.matrix.width or image.height > self.matrix.height:
            logging.debug("Image is larger than matrix, scaling down")
            # see which dimension is the constraining factor
            if image.width / self.matrix.width > image.height / self.matrix.height:
                # width is constraining factor
                factor = self.matrix.width / image.width
            else:
                # height is constraining factor
                factor = self.matrix.height / image.height
            scaled_width = math.floor(image.width * factor)
            scaled_height = math.floor(image.height * factor)
            logging.debug(f"Scale factor is {factor}, scaling image from {image.width} x {image.height} to "
                          f"{scaled_width} x {scaled_height}")
            image = image.resize((scaled_width, scaled_height),  Image.ANTIALIAS)
            logging.debug(f"Image size is now {image.width} x {image.height} after scaling")
        else:
            logging.debug(f"Image size is {image.width} x {image.height}, so no scaling needed")

        double_buffer = self.matrix.CreateFrameCanvas()
        img_width, img_height = image.size

        # let's scroll
        x_pos = round(max((self.matrix.width - img_width) / 2, 0))
        y_pos = round(max((self.matrix.height - img_height) / 2, 0))
        logging.debug(f"Positioning the image at ({x_pos}, {y_pos})")

        logging.debug(f"Matrix configuration:")
        logging.debug(f"    hardware_mapping:  {self.options.hardware_mapping}")
        logging.debug(f"    rows:  {self.options.rows}")
        logging.debug(f"    cols:  {self.options.cols}")
        logging.debug(f"    chain_length:  {self.options.chain_length}")
        logging.debug(f"    parallel:  {self.options.parallel}")
        logging.debug(f"    row_address_type:  {self.options.row_address_type}")
        logging.debug(f"    multiplexing:  {self.options.multiplexing}")
        logging.debug(f"    pwm_bits:  {self.options.pwm_bits}")
        logging.debug(f"    brightness:  {self.options.brightness}")
        logging.debug(f"    pwm_lsb_nanoseconds:  {self.options.pwm_lsb_nanoseconds}")
        logging.debug(f"    led_rgb_sequence:  {self.options.led_rgb_sequence}")
        logging.debug(f"    pixel_mapper_config:  {self.options.pixel_mapper_config}")
        logging.debug(f"    panel_type:  {self.options.panel_type}")
        logging.debug(f"    show_refresh_rate:  {self.options.show_refresh_rate}")
        logging.debug(f"    gpio_slowdown:  {self.options.gpio_slowdown}")
        logging.debug(f"    disable_hardware_pulsing:  {self.options.disable_hardware_pulsing}")
        logging.debug(f"    drop_privileges:  {self.options.drop_privileges}")

        logging.debug(f"Drawing image")
        double_buffer.SetImage(image, x_pos, y_pos)

        double_buffer = self.matrix.SwapOnVSync(double_buffer)
        while True:
            time.sleep(1)


# Main function
# e.g. call with
#  sudo ./image-shower.py --chain=4
# if you have a chain of four
if __name__ == "__main__":
    image_shower = ImageShower()
    if not image_shower.process():
        image_shower.parser.print_help()
