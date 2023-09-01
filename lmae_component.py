from abc import ABCMeta, abstractmethod
from copy import deepcopy
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
        crop_width = self.crop_area[2] - self.crop_area[0]
        self.crop_actors = list()
        for actor in self.panels:
            actor.set_position((self.position[0] + offset, self.position[1]))
            offset += crop_width
            self.crop_actors.append(CropMask(name=f"{name} crop mask for {actor.name}",
                                             crop_area=crop_area, child=actor))

    def get_animations(self) -> List[Animation]:
        self.logger.debug("Getting animations")
        base_animations = list()
        total_actor_width = sum(actor.size[0] for actor in self.panels)
        for i, actor in enumerate(self.panels):
            self.logger.debug(f"Constructing base animations for panel {i+1}")
            still = Still(name=f"wait {i+1}", duration=self.dwell_time)
            base_animations.append(still)
            self.logger.debug(f"    Base animation for still: {still.duration:.1f}s")
            if i < len(self.panels) - 1:
                move = StraightMove(name=f"transition{i+1}", duration=self.transition_time,
                                    easing=self.easing, distance=(-actor.size[0], 0))
                base_animations.append(move)
                self.logger.debug(f"    Base animation for straight move: {move.distance} over {move.duration:.1f}s")
            else:
                reset_move = StraightMove(name=f"reset transition", duration=self.transition_time,
                                          easing=self.easing, distance=(total_actor_width, 0))
                base_animations.append(reset_move)
                self.logger.debug(f"    Base animation for straight move: {reset_move.distance} over "
                                  f"{reset_move.duration:.1f}s")

        self.logger.debug(f"Constructed {len(base_animations)} base animations")

        animation_sequences = list()
        for actor in self.panels:
            self.logger.debug(f"Tailoring base animations for actor {actor.name}")
            anims_for_sequence = list()
            for anim in base_animations:
                actor_anim = deepcopy(anim)
                actor_anim.actor = actor
                anims_for_sequence.append(actor_anim)
            self.logger.debug(f"   Constructed {len(anims_for_sequence)} animations for sequence for {actor.name}")
            sequence = Sequence(name=f"Carousel sequence for {actor.name}", actor=actor, animations=anims_for_sequence,
                                repeat=True)
            animation_sequences.append(sequence)
        return animation_sequences

    def needs_render(self):
        need = any(crop.needs_render() for crop in self.crop_actors)
        # self.logger.debug(f"Carousel needs render? {need}")
        return need

    def render(self, canvas: Canvas):
        # self.logger.debug("Rendering carousel")
        for actor in self.panels:
            actor.render(canvas)
        self.changes_since_last_render = False
