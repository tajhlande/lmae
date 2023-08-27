import logging
from lmae_core import Actor, Animation, _get_sequential_name


class LinearMove(Animation):
    """
    This moves an actor a certain distance in a particular direction at a constant rate
    over a period of time.  It is designed to function as additive movement
    when combined with other animations.
    """

    def __init__(self, name: str = None, actor: Actor = None, repeat: bool = False,
                 distance: tuple[int, int] = None, duration: float = 1.0):
        name = name or _get_sequential_name("LinearMove")
        super().__init__(name=name, actor=actor, repeat=repeat, duration=duration)
        self.distance = distance or [0, 0]
        self.start_position = actor.position
        self.accumulated_movement = [0, 0]
        self.logger = logging.getLogger("name")

    def is_finished(self) -> bool:
        return self.get_simulated_time() > self.duration

    def start(self, current_time: float):
        super().start(current_time)
        self.start_position: tuple[int, int] = self.actor.position

    def update_actor(self, current_time: float):
        #  all times relative to start
        elapsed_time = self.get_elapsed_time(current_time)
        simulated_time = self.get_simulated_time()
        action_time = elapsed_time
        if elapsed_time > self.duration:
            action_time = self.duration
        action_fraction = 0.0 if self.duration == 0 else action_time / self.duration
        self.logger.debug(f"Updating animation {self.name} on actor {self.actor.name}. "
                          f"simulated: {simulated_time:.3f}s, elapsed: {elapsed_time:.3f}s, "
                          f"fraction: {action_fraction:.3f}")

        # interpolate movement
        d_x = round(self.distance[0] * action_fraction)
        d_y = round(self.distance[1] * action_fraction)

        # subtract accumulated movement
        net_d_x = d_x - self.accumulated_movement[0]
        net_d_y = d_y - self.accumulated_movement[1]

        # apply movement
        x = self.actor.position[0] + net_d_x
        y = self.actor.position[1] + net_d_y
        self.actor.position = [x, y]
        self.logger.debug(f"gross interp mvmt: {[d_x, d_y]}, accum mvmt: {self.accumulated_movement}, "
                          f"net mvmt: {[net_d_x, net_d_y]}")

        # account for movement
        self.accumulated_movement = [self.accumulated_movement[0] + net_d_x, self.accumulated_movement[1] + net_d_y]

        # finally
        self.set_update_time(current_time)


class Sequence(Animation):

    def __init__(self, name: str = None, actor: Actor = None, repeat: bool = False, animations: list[Animation] = None):
        name = name or _get_sequential_name("Sequence")
        super().__init__(name=name, actor=actor, repeat=repeat)
        self.animations = animations or list()
        self.seq_index = -1
        self.seq_start_time = 0
        self._compute_duration()
        self.logger = logging.getLogger(self.name)

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
        self.logger.debug("reset")
        super().reset()
        for anim in self.animations:
            anim.reset()
        self.seq_index = -1
        self.seq_start_time = 0

    def start(self, current_time: float):
        self.logger.debug("start")
        super().start(current_time)
        self.seq_index = 0
        self.seq_start_time = current_time

    def is_finished(self) -> bool:
        return self.seq_index >= len(self.animations)

    def update_actor(self, current_time: float):
        if self.seq_index >= len(self.animations):
            self.logger("All animations finished")
            return  # nothing to do, we're done

        current_anim = self.animations[self.seq_index]
        if current_anim.is_finished():
            self.logger(f"Animation {self.seq_index} finished, looking for next")
            self.seq_index += 1
            if self.seq_index >= len(self.animations):
                self.logger("All animations finished")
                return  # nothing to do, we're done
            current_anim = self.animations[self.seq_index]

        if not current_anim.is_started():
            self.logger(f"Starting animation {self.seq_index}")
            current_anim.start(current_time)
            self.seq_start_time = current_time

        current_anim.update_actor(current_time)

        self.set_update_time(current_time)