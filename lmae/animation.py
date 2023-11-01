import logging
from abc import abstractmethod

from colorsys import rgb_to_hsv, hsv_to_rgb
from enum import auto, Enum
from typing import Callable

from lmae.core import Actor, Animation, _get_sequential_name
from lmae.actor import StillImage, SpriteImage


class Still(Animation):
    """
    A  "no-op" animation that makes no changes to its actor. Useful for pausing in a sequence.
    """

    def __init__(self, name: str = None, actor: Actor = None, duration: float = 1.0):
        name = name or _get_sequential_name("Still")
        super().__init__(name, actor=actor, duration=duration)

    def update_actor(self, current_time: float):
        self.set_update_time(current_time)

    def is_finished(self) -> bool:
        return self.get_simulated_time() > self.duration


class Easing(Enum):
    """
    Easing function variations
    """
    LINEAR = auto()
    QUADRATIC = auto()
    BEZIER = auto()
    PARAMETRIC = auto()
    BACK = auto()
    CUSTOM = auto()


def _linear_easing(t: float):
    return t


def _quadratic_easing(t: float):
    if t <= 0.5:
        return 2.0 * t * t
    t -= 0.5
    return 2.0 * t * (1.0 - t) + 0.5


def _bezier_easing(t: float):
    return t * t * (3.0 - 2.0 * t)


def _parametric_easing(t: float):
    square_t = t * t
    return square_t / (2.0 * (square_t - t) + 1.0)


# constants for back easing
_eb_c1 = 1.70158
_eb_c2 = _eb_c1 * 1.525


def _back_easing(t: float):
    # c1 = StraightMove._eb_c1
    c2 = _eb_c2
    if t < 0.5:
        return (pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2)) / 2
    else:
        return (pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2


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
        name = name or _get_sequential_name("StraightMove")
        super().__init__(name=name, actor=actor, repeat=repeat, duration=duration)
        self.distance = distance or (0, 0)
        self.accumulated_movement = (0, 0)
        self.easing = None
        self.easing_function = None
        self.set_easing(easing)
        self.logger = logging.getLogger(name)

    def set_easing(self, easing: Easing):
        """
        Set the easing method for this motion.
        :param easing: The easing enum value
        """
        self.easing = easing
        if self.easing == Easing.QUADRATIC:
            self.set_easing_function(_quadratic_easing, easing=easing)
        elif self.easing == Easing.BEZIER:
            self.set_easing_function(_bezier_easing, easing=easing)
        elif self.easing == Easing.PARAMETRIC:
            self.set_easing_function(_parametric_easing, easing=easing)
        elif self.easing == Easing.BACK:
            self.set_easing_function(_back_easing, easing=easing)
        else:
            self.set_easing_function(_linear_easing, easing=easing)

    def set_easing_function(self, easing_function: Callable[[float], float], easing: Easing = Easing.CUSTOM):
        """
        To set a custom function for easing
        :param easing_function: A function that takes a float t: 0 <= t <= 1 and returns a float t: 0 <= t <= 1
        :param easing: If setting a provided easing function, set this to the matching enum value
        """
        # self.logger.debug(f"Setting easing to {easing.name}")
        self.easing_function = easing_function
        self.easing = easing

    def reset(self):
        super().reset()
        self.accumulated_movement = (0, 0)

    def is_finished(self) -> bool:
        return self.get_simulated_time() > self.duration

    def start(self, current_time: float):
        super().start(current_time)

    def update_actor(self, current_time: float):
        #  all times relative to start
        elapsed_time = self.get_elapsed_time(current_time)
        # simulated_time = self.get_simulated_time()
        action_time = elapsed_time
        if elapsed_time > self.duration:
            action_time = self.duration
        duration_fraction = 0.0 if self.duration == 0 else action_time / self.duration
        easing_fraction = self.easing_function(duration_fraction)

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
        #                  f"net mvmt: {(net_d_x, net_d_y)}, actor at {self.actor.position}")

        # account for movement
        self.accumulated_movement = (self.accumulated_movement[0] + net_d_x, self.accumulated_movement[1] + net_d_y)

        # finally
        if net_d_x != 0 or net_d_y != 0:
            # self.logger.debug(f"Setting actor {self.actor.name} changes_since_last_render to True")
            self.actor.changes_since_last_render = True
        self.set_update_time(current_time)


class _SetVisibility(Animation):

    def __init__(self, name: str = None, actor: Actor = None, visible: bool = True):
        name = name or _get_sequential_name("_SetVisibility")
        super().__init__(name=name, actor=actor, duration=0.001)  # pretty sure if this was 0.0, bad things would happen
        self.visible = visible

    def is_finished(self) -> bool:
        return self.get_simulated_time() > self.duration

    def update_actor(self, current_time: float):
        if self.visible != self.actor.visible:
            self.actor.set_visible(self.visible)
            self.actor.changes_since_last_render = True
        self.set_update_time(current_time)


class Show(_SetVisibility):
    def __init__(self, name: str = None, actor: Actor = None):
        name = name or _get_sequential_name(f"Show {actor.name}")
        super().__init__(name=name, actor=actor, visible=True)


class Hide(_SetVisibility):
    def __init__(self, name: str = None, actor: Actor = None):
        name = name or _get_sequential_name(f"Hide {actor.name}")
        super().__init__(name=name, actor=actor, visible=False)


class Sequence(Animation):

    def __init__(self, name: str = None, actor: Actor = None, repeat: bool = False, animations: list[Animation] = None):
        name = name or _get_sequential_name("Sequence")
        super().__init__(name=name, actor=actor, repeat=repeat)
        self.animations = animations or list()
        # self.logger.debug(f"We have {len(self.animations)} animations in this sequence")
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
        # self.logger.debug(f"computed duration is {self.duration:.1f}s")

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
            # if current_anim:
            #     if current_anim.actor:
            #         self.logger.debug(f"Starting animation {self.seq_index} ({current_anim.name}) for {current_anim.actor.name}")
            #     else:
            #         self.logger.warning(f"Starting animation {self.seq_index} ({current_anim.name}) for None actor")
            # else:
            #     self.logger.warning(f"Starting animation {self.seq_index} (None)")

            current_anim.start(current_time)
            self.seq_start_time = current_time

        current_anim.update_actor(current_time)

        self.set_update_time(current_time)


class HueRotate(Animation):
    """
    Cycle a color around the hue wheel in HSV space. This animation can be applied to any
    actor that has color settings, but because they are different (some have one color setting,
    some have multiple), the mechanism here to update the actor is through a callback function
    that the user must provide.
    """
    def __init__(self, name: str = None, actor: Actor = None, initial_color: tuple[int, int, int] = (255, 255, 255),
                 duration: float = 10.0, callback: Callable[[tuple[int, int, int]], None] = None,
                 repeat: bool = False):
        """

        :param name: Optional name for this animation
        :param actor: The actor to which this animation applies
        :param initial_color: The starting color.  When the animation finishes, this will be the finish color as well.
        :param duration: How long it takes to cycle around the wheel, in seconds
        :param callback: A function that applies the color argument to the actor
        :param repeat: Whether or not this animation should repeat.
        """
        name = name or _get_sequential_name("HueRotate")
        super().__init__(name=name, actor=actor, duration=duration, repeat=repeat)
        self.logger.debug(f"Repeat: {self.repeat}")
        self.initial_hsv = rgb_to_hsv(initial_color[0] / 255.0, initial_color[1] / 255.0, initial_color[2] / 255.0)
        self.color_set_callback: Callable[[tuple[int, int, int]], None] = callback

    def is_finished(self) -> bool:
        return self.get_simulated_time() > self.duration

    def update_actor(self, current_time: float):
        #  all times relative to start
        elapsed_time = self.get_elapsed_time(current_time)
        action_time = elapsed_time
        if elapsed_time > self.duration:
            action_time = self.duration
        duration_fraction = 0.0 if self.duration == 0 else action_time / self.duration

        adjusted_hue = self.initial_hsv[0] + duration_fraction
        while adjusted_hue >= 1.0:
            adjusted_hue = adjusted_hue - 1.0

        float_rgb_color = hsv_to_rgb(adjusted_hue, self.initial_hsv[1], self.initial_hsv[2])
        rgb_color = round(float_rgb_color[0] * 255), round(float_rgb_color[1] * 255), round(float_rgb_color[2] * 255)
        self.color_set_callback(rgb_color)
        self.set_update_time(current_time)


class FrameSequence(Animation):
    """
    A container for animated image sequence information. Frame count, frame list, with durations for each frame.
    Repeat or not.
    """
    def __init__(self, name: str = None, actor: Actor = None, repeat: bool = False):
        name = name or _get_sequential_name("FrameSequence")
        # we will update with true duration later
        super().__init__(name=name, actor=actor, duration=1.0, repeat=repeat)
        self.frames_info = []

    def add_frame(self, frame_name: str, duration: float = 1.0/6, recompute: bool = True):
        """
        Add a single frame to this sequence.
        :param frame_name: The name of the frame
        :param duration: How long this frame should be shown. Defaults to 1/6 of a second.
        :param recompute: whether or not to recompute aggregate times. Defaults to True.
        """
        self.add_frame_info({
            "name": frame_name,
            "duration": duration
        }, recompute)

    def reset_frame_info(self):
        self.frames_info = []

    def add_frame_info(self, frame_info: dict[str, float], recompute: bool = True):
        """
        Add a frame info dictionary to this sequence
        :param frame_info: The frame info dictionary. Should have "name" and "duration" set as string and float.
        :param recompute: whether or not to recompute aggregate times. Defaults to True.
        """
        self.frames_info.append(frame_info)
        if recompute:
            self.compute_aggregated_times()

    def compute_aggregated_times(self):
        """
        Computes the offset start times for each frame in the sequence.
        """
        accum_duration = 0.0
        for frame_info in self.frames_info:
            frame_info["start_time"] = accum_duration
            accum_duration += frame_info["duration"]
            self.logger.debug(f"Starting frame {frame_info['name']} at {frame_info['start_time']} "
                              f"with duration {frame_info['duration']}")
        self.duration = accum_duration

    @abstractmethod
    def set_actor_frame(self, frame_name: str):
        pass

    def update_actor(self, current_time: float):
        elapsed_time = self.get_elapsed_time(current_time)

        # find frame that matches current elapsed time
        # this might be made more efficient by recording the current frame somewhere and using that info to
        # reduce what is examined, but these lists are generally short, so...
        # self.logger.debug(f"elapsed time: {elapsed_time}, frame count: {len(self.frames_info)}")
        frame_info = None
        i = 0
        while not frame_info and i < len(self.frames_info):
            cf = self.frames_info[i]
            cf_finish_time = cf['start_time'] + cf['duration']
            # self.logger.debug(f"Checking frame: start time {cf['start_time']}, elapsed time {elapsed_time}, "
            #                   f"finish time: {cf_finish_time}")
            if cf['start_time'] <= elapsed_time < cf_finish_time:
                frame_info = cf
                # self.logger.debug(f"Found winner: {frame_info['name']}")
            i = i + 1
        if frame_info:
            self.set_actor_frame(frame_info["name"])
        else:
            self.logger.warning(f"No matching frame found for elapsed time {elapsed_time}")
        self.set_update_time(current_time)

    def is_finished(self) -> bool:
        return self.get_simulated_time() > self.duration

    def reset(self):
        super().reset()


class SpriteSequence(FrameSequence):
    """
    An animation that can be used to set frames on a sprite.
    """
    def __init__(self,  name: str = None, sprite_image: SpriteImage = None, repeat: bool = False):
        """
        Create a sprite sequence animation for a sprite image actor.
        :param name: The name for this animation
        :param sprite_image: The sprite image actor
        :param repeat: Whether or not to repeat this animation. Defaults to False.
        """
        name = name or _get_sequential_name("SpriteSequence")
        # we will update with true duration later
        super().__init__(name=name, actor=sprite_image, repeat=repeat)
        self.sprite_image = sprite_image

    def set_actor_frame(self, frame_name: str):
        self.sprite_image.set_sprite(frame_name)


class AnimatedImageSequence(FrameSequence):
    """
    An animation that can be used to set frames on an image actor containing a PIL image with an image sequence.
    """
    def __init__(self,  name: str = None, still_image: StillImage = None, repeat: bool = False):
        """
        Create an image sequence animation for a still image actor that contains a PIL image with an image sequence.
        :param name: The name for this animation.
        :param still_image: The still image actor for this animation.
        :param repeat: Whether or not to repeat this animation. Defaults to False.
        :raise Exception: if the PIL image in the actor does not have an `is_animated` attribute set to `true`
        """
        name = name or _get_sequential_name("AnimatedImageSequence")
        # we will update with true duration later
        super().__init__(name=name, actor=still_image, repeat=repeat)

        # make sure the actor
        if not getattr(still_image.image, "is_animated", False):
            raise Exception("AnimatedImageSequence is expecting an actor with an image sequence")
        self.still_image = still_image

    def set_actor_frame(self, frame_name: str):
        self.still_image.image.seek(int(frame_name))

    def get_frames_from_image(self):
        image = self.still_image.image
        if image:

            for i in range(0, image.n_frame):
                image.seek(i)
                self.add_frame(str(i), image.info['duration'], False)

            self.compute_aggregated_times()
