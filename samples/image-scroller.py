#!/usr/bin/env python
import time
from samplebase import SampleBase
from PIL import Image


class ImageScroller(SampleBase):
    def __init__(self, *args, **kwargs):
        super(ImageScroller, self).__init__(*args, **kwargs)
        self.image = None
        self.parser.add_argument("-i", "--image", help="The image to display",
                                 default="../../../examples-api-use/runtext.ppm")

    def run(self):
        if 'image' not in self.__dict__:
            self.image = Image.open(self.args.image).convert('RGB')
        self.image.resize((self.matrix.width, self.matrix.height), Image.ANTIALIAS)

        double_buffer = self.matrix.CreateFrameCanvas()
        img_width, img_height = self.image.size

        # let's scroll
        x_pos = 0
        while True:
            x_pos += 1
            if x_pos > img_width:
                x_pos = 0

            double_buffer.SetImage(self.image, -x_pos)
            double_buffer.SetImage(self.image, -x_pos + img_width)

            double_buffer = self.matrix.SwapOnVSync(double_buffer)
            time.sleep(0.01)


# Main function
# e.g. call with
#  sudo ./image-scroller.py --chain=4
# if you have a chain of four
if __name__ == "__main__":
    image_scroller = ImageScroller()
    if not image_scroller.process():
        image_scroller.print_help()
