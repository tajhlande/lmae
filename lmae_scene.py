import time
from lmae_core import LMAEObject, Stage, Actor, _get_sequential_name



class Scene(Stage):
    """
    A stage with actors that can be animated
    """

    def __init__(self, name: str = None):
        name = name or _get_sequential_name("Scene")  # 'Canvas_' + f'{randrange(65536):04X}'
        super().__init__(name=name)

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
