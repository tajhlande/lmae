import time
from lmae_core import LMAEObject, Stage, Actor, _get_sequential_name


class Animation(LMAEObject):
    """
    A clock based way to update an actor based on elapsed time
    """

    def __init__(self, name: str = None, actor: Actor = None):
        name = name or _get_sequential_name("Animation")  # 'Canvas_' + f'{randrange(65536):04X}'
        super().__init__(name=name)
        self.start_time: float = 0
        self.end_time: float = 0
        self.frame_count: int = 0

    def reset(self):
        self.start_time = 0
        self.end_time = 0
        self.frame_count = 0

    def start(self):
        self.start_time = time.time()

    def end(self):
        pass

    def elapsed(self) -> float:
        if self.start_time == 0:
            return 0
        if self.end_time == 0:
            return time.time() - self.start_time

        return self.end_time - self.start_time


class Scene(LMAEObject):
    """
    A collection of a stage and actors that can be animated
    """

    def __init__(self, stage: Stage, name: str = None):
        name = name or _get_sequential_name("Scene")  # 'Canvas_' + f'{randrange(65536):04X}'
        super().__init__(name=name)
        self.stage = Stage()



