import logging
from enum import Enum
from lmae_core import Actor, Animation, _get_sequential_name


class Easing(Enum):
    """
    Easing function variations
    """
    LINEAR = "linear"
    QUADRATIC = "quadratic"
    BEZIER = "bezier"
    PARAMETRIC = "parametric"


class StraightMove(Animation):
    """
    This moves an actor a certain distance straight in a particular direction
    at a certain rate over a period of time.  It is designed to function as additive movement
    when combined with other animations.
    The rate can be linear, quadratic, Bézier, or parametric.
    Thanks to  https://stackoverflow.com/questions/13462001/ease-in-and-ease-out-animation-formula for the formulas.
    More easing formulas can be found here: https://gizma.com/easing/
    """

    def __init__(self, name: str = None, actor: Actor = None, repeat: bool = False,
                 distance: tuple[int, int] = None, duration: float = 1.0,
                 easing: Easing = Easing.LINEAR):
        name = name or _get_sequential_name("LinearMove")
        super().__init__(name=name, actor=actor, repeat=repeat, duration=duration)
        self.distance = distance or (0, 0)
        self.accumulated_movement = (0, 0)
        self.easing = easing
        self.logger = logging.getLogger(name)
        self.logger.debug(f"Easing function is {self.easing}")

    def reset(self):
        super().reset()
        self.accumulated_movement = (0, 0)

    def is_finished(self) -> bool:
        return self.get_simulated_time() > self.duration

    def start(self, current_time: float):
        super().start(current_time)

    @staticmethod
    def _quadratic_easing(t: float):
        if t <= 0.5:
            return 2.0 * t * t
        t -= 0.5
        return 2.0 * t * (1.0 - t) + 0.5

    @staticmethod
    def _bezier_easing(t: float):
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def _parametric_easing(t: float):
        square_t = t * t
        return square_t / (2.0 * (square_t - t) + 1.0)

    def update_actor(self, current_time: float):
        #  all times relative to start
        elapsed_time = self.get_elapsed_time(current_time)
        simulated_time = self.get_simulated_time()
        action_time = elapsed_time
        if elapsed_time > self.duration:
            action_time = self.duration
        duration_fraction = 0.0 if self.duration == 0 else action_time / self.duration

        if self.easing == Easing.QUADRATIC:
            easing_fraction = self._quadratic_easing(duration_fraction)
        elif self.easing == Easing.BEZIER:
            easing_fraction = self._bezier_easing(duration_fraction)
        elif self.easing == Easing.PARAMETRIC:
            easing_fraction = self._parametric_easing(duration_fraction)
        else:
            easing_fraction = duration_fraction

        # self.logger.debug(f"Updating animation {self.name} on actor {self.actor.name} at {current_time:.3f}. "
        #                   f"simulated: {simulated_time:.3f}s, elapsed: {elapsed_time:.3f}s, "
        #                   f"duration fraction: {duration_fraction:.3f}, easing fraction: {easing_fraction:.3f}")

        # interpolate movement
        d_x = round(self.distance[0] * easing_fraction)
        d_y = round(self.distance[1] * easing_fraction)

        # subtract accumulated movement
        net_d_x = d_x - self.accumulated_movement[0]
        net_d_y = d_y - self.accumulated_movement[1]

        # apply movement
        x = self.actor.position[0] + net_d_x
        y = self.actor.position[1] + net_d_y
        self.actor.position = (x, y)
        # self.logger.debug(f"gross interp mvmt: {(d_x, d_y)}, accum mvmt: {self.accumulated_movement}, "
        #                   f"net mvmt: {(net_d_x, net_d_y)}, actor at {self.actor.position}")

        # account for movement
        self.accumulated_movement = (self.accumulated_movement[0] + net_d_x, self.accumulated_movement[1] + net_d_y)

        # finally
        if net_d_x != 0 or net_d_y != 0:
            # self.logger.debug(f"Setting actor {self.actor.name} changes_since_last_render to True")
            self.actor.changes_since_last_render = True
        self.set_update_time(current_time)


class Sequence(Animation):

    def __init__(self, name: str = None, actor: Actor = None, repeat: bool = False, animations: list[Animation] = None):
        name = name or _get_sequential_name("Sequence")
        super().__init__(name=name, actor=actor, repeat=repeat)
        self.animations = animations or list()
        self.logger.debug(f"We have {len(self.animations)} animations in this sequence")
        self.seq_index = -1
        self.seq_start_time = 0
        self._compute_duration()

    def add_animations(self, *args: Animation):
        self.animations.extend(args)
        self._compute_duration()

    def _compute_duration(self):
        duration = 0.0
        for anim in self.animations:
            duration += anim.duration
        self.duration = duration
        self.logger.debug(f"computed duration is {self.duration}")

    def reset(self):
        # self.logger.debug("reset")
        super().reset()
        for anim in self.animations:
            anim.reset()
        self.seq_index = -1
        self.seq_start_time = 0

    def start(self, current_time: float):
        # self.logger.debug("start")
        super().start(current_time)
        self.seq_index = 0
        self.seq_start_time = current_time

    def is_finished(self) -> bool:
        return self.seq_index >= len(self.animations)

    def update_actor(self, current_time: float):
        if self.seq_index >= len(self.animations):
            # self.logger.debug("All animations finished")
            return  # nothing to do, we're done

        current_anim = self.animations[self.seq_index]
        if current_anim.is_finished():
            # self.logger.debug(f"Animation {self.seq_index} finished, looking for next")
            self.seq_index += 1
            if self.seq_index >= len(self.animations):
                # self.logger.debug("All animations finished")
                return  # nothing to do, we're done
            current_anim = self.animations[self.seq_index]

        if not current_anim.is_started():
            # self.logger.debug(f"Starting animation {self.seq_index}")
            current_anim.start(current_time)
            self.seq_start_time = current_time

        current_anim.update_actor(current_time)

        self.set_update_time(current_time)
