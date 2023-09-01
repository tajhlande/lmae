from abc import ABCMeta, abstractmethod
from typing import List

from lmae_core import Actor, Animation, Canvas, _get_sequential_name
from lmae_actor import CropMask
from lmae_animation import Easing, Sequence, Still, StraightMove


class LMAEComponent(Actor, metaclass=ABCMeta):
    """
    An actor that is able to self-generate animations.
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
                 dwell_time: float = 10.0, transition_time: float = 1.2, easing: Easing = Easing.QUADRATIC,
                 crop_area: tuple[int, int, int, int] = (16, 8, 47, 23)):
        name = name or _get_sequential_name("Carousel")
        super().__init__(name, position)
        self.dwell_time = dwell_time
        self.transition_time = transition_time
        self.easing = easing
        self.panels = panels or list()

        self.crop_area = crop_area

        # set up actor panel positioning and crops
        offset = 0
        spacing = self.crop_area[2] - self.crop_area[0] + 2
        self.crop_actors = list()
        for actor in self.panels:
            actor.set_position((self.position[0] + offset, self.position[1]))
            offset += spacing
            self.crop_actors.append(CropMask(name=f"{name}_CropMask_{actor.name}",
                                             crop_area=crop_area, child=actor))
        self.logger.debug(f"Total crop actors: {len(self.crop_actors)}")

    def get_animations(self) -> List[Animation]:
        self.logger.debug("Constructing individual animations")
        animations = dict((actor.name, list()) for actor in self.panels)
        crop_width = self.crop_area[2] - self.crop_area[0]
        total_carousel_width = crop_width * (len(self.panels) - 1)
        self.logger.debug(f"Crop width: {crop_width}, total carousel width: {total_carousel_width}")

        for i, actor in enumerate(self.panels):
            for actor2 in self.panels:
                still = Still(name=f"Wait {i+1} for {actor2.name}", duration=self.dwell_time, actor=actor2)
                animations[actor2.name].append(still)
                self.logger.debug(f"    Wait animation {i+1} for {actor2.name}: {still.duration:.1f}s")
            if i < len(self.panels) - 1:
                for actor2 in self.panels:
                    move = StraightMove(name=f"Slide {i+1} for {actor2.name}", duration=self.transition_time,
                                        easing=self.easing, distance=(-crop_width, 0), actor=actor2)
                    animations[actor2.name].append(move)
                    self.logger.debug(f"    Slide animation {i+1} for {actor2.name}: {move.distance} over "
                                      f"{move.duration:.1f}s")
            else:
                for actor2 in self.panels:
                    reset_move = StraightMove(name=f"Reset for {actor2.name}", duration=self.transition_time,
                                              easing=self.easing, distance=(total_carousel_width, 0), actor=actor2)
                    animations[actor2.name].append(reset_move)
                    self.logger.debug(f"    Reset animation for {actor2.name}: {reset_move.distance} over "
                                      f"{reset_move.duration:.1f}s")

        self.logger.debug(f"Constructing sequences")
        animation_sequences = list()
        for actor in self.panels:
            sequence = Sequence(name=f"Carousel sequence for {actor.name}", actor=actor,
                                animations=animations[actor.name], repeat=True)
            animation_sequences.append(sequence)
            self.logger.debug(f"   Constructed sequence anim with {len(animation_sequences)} animations for {actor.name}")
        return animation_sequences

    def needs_render(self):
        need = any(crop.needs_render() for crop in self.crop_actors)
        # self.logger.debug(f"Carousel needs render? {need}")
        return need

    def render(self, canvas: Canvas):
        # self.logger.debug("Rendering carousel")
        for actor in self.crop_actors:
            actor.render(canvas)
        self.changes_since_last_render = False
