import time
from lmae_core import LMAEObject, Stage, Actor, _get_sequential_name


class UnimplementedMethodError(AssertionError):
    pass


class Animation(LMAEObject):
    """
    A clock based way to update an actor based on elapsed time
    """

    def __init__(self, name: str = None, actor: Actor = None):
        name = name or _get_sequential_name("Animation")  # 'Canvas_' + f'{randrange(65536):04X}'
        super().__init__(name=name)
        self.actor = actor
        self.start_time: float = 0
        self.last_render_time: float = 0
        self.end_time: float = 0
        self.frame_count: int = 0

    def reset(self):
        self.start_time = 0
        self.last_render_time = 0
        self.end_time = 0
        self.frame_count = 0

    def start(self, current_time: float):
        self.start_time = current_time

    def is_started(self):
        return self.start_time == 0

    def elapsed(self) -> float:
        if self.start_time == 0:
            return 0
        if self.end_time == 0:
            return self.last_render_time - self.start_time

        return self.end_time - self.start_time

    def is_finished(self) -> bool:
        """
        Override this to indicate when an animation is done.
        This should usually be based on the current time in the last call to `update_actor(current_time)`
        :return: `True` if this animation is finished, `False` otherwise
        """
        raise UnimplementedMethodError("Need to override is_finished() in subclasses of Animation")

    def update_actor(self, current_time: float):
        """
        Override this to update this animation's actor based on the current time.

        Actors must correctly reflect their state of needing to be rendered after being updated.
        If updating would cause any changes in the way an actor is rendered, then
        `actor.changes_since_last_render` must be `True`. If updating did not cause any changes in the way
        an actor is rendered, then `actor.changes_since_last_render` must be `False`.

        :param current_time: the current time that this frame is being rendered
        """
        raise UnimplementedMethodError("Need to override update_actor(current_time) in subclasses of Animation")


class Scene(Stage):
    """
    A stage with actors that can be animated
    """

    def __init__(self, name: str = None):
        name = name or _get_sequential_name("Scene")  # 'Canvas_' + f'{randrange(65536):04X}'
        super().__init__(name=name)
        self.animations: list[Animation] = []

    def add_animation(self, animation: Animation):
        self.animations.append(animation)

    def render_frame(self):
        current_time = time.perf_counter()

        # run all the animations
        for anim in self.animations:
            # see if we need to start them
            if not anim.is_started():
                anim.start(current_time)

            # update each animation
            anim.update_actor(current_time)
            anim.last_render_time = current_time

        # see if we need to update
        needs_render = False
        for actor in self.actors:
            needs_render = needs_render or actor.changes_since_last_render

        # render if needed
        if needs_render:
            self.prepare_frame()
            self.render_actors()
            self.display_frame()
        else:
            pass  # no update needed

        # clean up finished animations
        self.animations[:] = [anim for anim in self.animations if not anim.is_finished()]
