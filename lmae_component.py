from abc import ABCMeta, abstractmethod
from typing import List

from lmae_core import Actor, Animation, Canvas, _get_sequential_name
from lmae_animation import Easing


class LMAEComponent(Actor, metaclass=ABCMeta):
    """
    An actor that is able to self-generate animations.
    If the
    """

    def __init__(self, name: str = None, position: tuple[int, int] = (0, 0)):
        name = name or _get_sequential_name("LMAEComponent")
        super().__init__(name, position)

    @abstractmethod
    def get_animations(self) -> List[Animation]:
        pass


class Carousel(LMAEComponent):
    """
    A visual container that rotates display of multiple panels (child actors)
    with a certain dwell time on each actor and movement transitions between them.
    """

    def __init__(self, name: str = None, position: tuple[int, int] = (0, 0), panels: List[Actor] = None,
                 dwell_time: float = 10.0, transition_time: float = 1.2, easing: Easing = Easing.QUADRATIC):
        name = name or _get_sequential_name("Carousel")
        super().__init__(name, position)
        self.dwell_time = dwell_time
        self.transition_time = transition_time
        self.easing = easing
        self.panels = panels or list()

    def add_panel(self, panel: Actor):
        self.panels.append(panel)

    def add_panels(self, *args: Actor):
        self.panels.extend(args)

    def get_animations(self) -> List[Animation]:
        pass

    def render(self, canvas: Canvas):
        pass
