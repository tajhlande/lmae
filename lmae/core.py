# Core classes for LED Matrix Animation Engine

from PIL import Image, ImageDraw


class LMAEObject:
    def __init__(self, *args, **kwargs):
        pass


class Canvas(LMAEObject):
    def __init__(self, *args, **kwargs):
        super(LMAEObject, self).__init__(*args, **kwargs)
        self.image = Image.new("RGB", (64, 32), (0, 0, 0))
        self.image_draw = ImageDraw.Draw(self.image)
        pass


class Actor(LMAEObject):
    def __init__(self, *args, **kwargs):
        super(LMAEObject, self).__init__(*args, **kwargs)
        self.position = 0, 0
        self.size = 0, 0
        pass

    def render(self, canvas: Canvas):
        pass


class StillImage(Actor):
    def __init__(self, *args, **kwargs):
        super(LMAEObject, self).__init__(*args, **kwargs)
        self.position = 0, 0
        self.size = 0, 0
        pass


class Stage(LMAEObject):
    def __init__(self, *args, **kwargs):
        super(LMAEObject, self).__init__(*args, **kwargs)
        self.size = 64, 32       # size in pixels
        self.actors = dict()
        pass


