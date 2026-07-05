from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image, ImageSequence

from lmae.actor import CropMask, MultiFrameImage, SpriteImage
from lmae.animation import (
    AnimatedImageSequence,
    Easing,
    Sequence,
    SpriteSequence,
    Still,
    StraightMove,
)
from lmae.core import Actor, Animation, Canvas, _get_sequential_name


class LMAEComponent(Actor, ABC):
    """
    An actor that is able to self-generate animations.
    """

    def __init__(self, name: str | None = None, position: tuple[int, int] = (0, 0)):
        name = name or _get_sequential_name("LMAEComponent")
        super().__init__(name, position)

    @abstractmethod
    def get_animations(self) -> list[Animation]:
        pass


class Carousel(LMAEComponent):
    """
    A visual container that rotates display of multiple panels (child actors)
    with a certain dwell time on each actor and movement transitions between them.
    """

    def __init__(
        self,
        panels: list[Actor],
        name: str | None = None,
        position: tuple[int, int] = (0, 0),
        dwell_time: float = 10.0,
        transition_time: float = 1.2,
        easing: Easing = Easing.QUADRATIC,
        crop_area: tuple[int, int, int, int] = (16, 8, 47, 23),
        panel_offset: tuple[int, int] = (0, 0),
    ):
        name = name or _get_sequential_name("Carousel")
        super().__init__(name, position)
        self.dwell_time = dwell_time
        self.transition_time = transition_time
        self.easing = easing
        self.panels = panels

        self.crop_area = crop_area
        self.panel_offset = panel_offset

        # set up actor panel positioning and crops
        offset = 0
        spacing = self.crop_area[2] - self.crop_area[0] + 2
        self.crop_actors = list()
        for actor in self.panels:
            actor.set_position(
                (
                    self.position[0] + offset + self.panel_offset[0],
                    self.position[1] + panel_offset[1],
                )
            )
            offset += spacing
            self.crop_actors.append(
                CropMask(
                    name=f"{name}_CropMask_{actor.name}",
                    crop_area=crop_area,
                    child=actor,
                )
            )
        self.animations: list[Animation] = list()
        # self.logger.debug(f"Total crop actors: {len(self.crop_actors)}")

    def get_animations(self) -> list[Animation]:
        if not self.animations:
            self.logger.debug("Constructing individual animations")
            animations = dict((actor.name, list()) for actor in self.panels)
            spacing = self.crop_area[2] - self.crop_area[0] + 2
            total_carousel_width = spacing * (len(self.panels) - 1)
            self.logger.debug(f"Spacing: {spacing}, total carousel width: {total_carousel_width}")

            for i, _actor in enumerate(self.panels):
                for actor2 in self.panels:
                    still = Still(
                        name=f"Wait {i + 1} for {actor2.name}",
                        duration=self.dwell_time,
                        actor=actor2,
                    )
                    animations[actor2.name].append(still)
                if i < len(self.panels) - 1:
                    for actor2 in self.panels:
                        move = StraightMove(
                            name=f"Slide {i + 1} for {actor2.name}",
                            duration=self.transition_time,
                            easing=self.easing,
                            distance=(-spacing, 0),
                            actor=actor2,
                        )
                        animations[actor2.name].append(move)
                else:
                    for actor2 in self.panels:
                        reset_move = StraightMove(
                            name=f"Reset for {actor2.name}",
                            duration=self.transition_time,
                            easing=self.easing,
                            distance=(total_carousel_width, 0),
                            actor=actor2,
                        )
                        animations[actor2.name].append(reset_move)

            self.logger.debug("Constructing sequences")
            animation_sequences = []
            for actor in self.panels:
                sequence = Sequence(
                    name=f"Carousel sequence for {actor.name}",
                    actor=actor,
                    animations=animations[actor.name],
                    repeat=True,
                )
                animation_sequences.append(sequence)

            self.animations = animation_sequences

        return self.animations

    def needs_render(self):
        need = any(crop.needs_render() for crop in self.crop_actors)
        # self.logger.debug(f"Carousel needs render? {need}")
        return need

    def render(self, canvas: Canvas):
        # self.logger.debug("Rendering carousel")
        for actor in self.crop_actors:
            actor.render(canvas)
        self.changes_since_last_render = False


class AnimatedSprite(LMAEComponent):
    """
    An animated sprite image. Repeats by default.
    """

    def __init__(
        self,
        sprite: SpriteImage,
        frames: list[str],
        name: str | None = None,
        position: tuple[int, int] = (0, 0),
        duration: float = 1.0,
        repeat: bool = True,
    ):
        """
        Initialize an animated sprite actor
        :param name: The name of this image actor
        :param position: The initial position
        :param sprite: The sprite to animate
        :param frames: A list of sprite names for the sprite
        :param duration: The duration of the entire animation. Defaults to 1 second.
        :param repeat: Whether to repeat the animation. Defaults to True.
        """
        name = name or _get_sequential_name("AnimatedSprite")
        super().__init__(name=name, position=position)
        self.sprite = sprite
        self.sequence: SpriteSequence = SpriteSequence(
            name=name + "_Sequence", sprite_image=sprite, repeat=repeat
        )
        if frames:
            self.set_frame_sequence(frames, duration)

    def set_frame_sequence(self, frames: list[str], duration: float):
        """
        Set the frames for the animation. Will create an animation
        sequence with equal time per frame.

        :param frames: A list of sprite selection names
        :param duration: The duration for the entire sequence of frames
        """
        self.logger.debug(f"Setting frames from frame list of length {len(frames)}")
        if not frames:
            return
        duration_per_frame = duration / len(frames)
        for name in frames:
            self.logger.debug(f"Adding frame {name} with duration {duration_per_frame}")
            self.sequence.add_frame(name, duration_per_frame, False)
        self.sequence.compute_aggregated_times()

    def get_animations(self) -> list[Animation]:
        return [self.sequence]

    def render(self, canvas: Canvas):
        if self.sprite:
            self.sprite.render(canvas)

    def needs_render(self):
        return self.sprite.needs_render()

    def set_position(self, position: tuple[int, int]):
        super().set_position(position)
        if self.sprite:
            self.sprite.set_position(position)


class AnimatedImage(LMAEComponent):
    """
    An animated image. Repeats by default. Can be set from an animated gif that is
    loaded as a PIL image
    """

    def __init__(
        self,
        name: str | None = None,
        position: tuple[int, int] = (0, 0),
        pil_source_image: Image.Image | None = None,
        multi_frame_image: MultiFrameImage | None = None,
        repeat: bool = True,
    ):
        """
        Initialize an animated image actor.
        Set either `multi_frame_image` or `pil_source_image`, but not both.

        :param name: The name of this image actor
        :param position: The initial position
        :param pil_source_image: A PIL image with an image sequence in it.
        :param multi_frame_image: A MultiFrameImage that is already prepared.
        :param repeat: Whether to repeat the animation. Defaults to True.
        :raise Exception: if the PIL image in the actor does not have
            an `is_animated` attribute set to `true`
        """
        name = name or _get_sequential_name("AnimatedImage")
        super().__init__(name=name, position=position)
        self.repeat = repeat
        self.sequence: AnimatedImageSequence | None = None
        self.multi_frame_image: MultiFrameImage | None = multi_frame_image
        if pil_source_image:
            self.set_from_pil_image(pil_source_image)

    def set_from_pil_image(self, pil_image: Image):
        self.sequence: AnimatedImageSequence = AnimatedImageSequence(
            name=self.name + "_Sequence",
            actor=self.multi_frame_image,
            repeat=self.repeat,
        )

        images = []
        index = 0
        self.sequence.reset_frame_info()
        for frame in ImageSequence.Iterator(pil_image):
            frame_image: Image = frame.copy()
            duration: float = (
                frame.info["duration"] / 1000.0 if frame.info["duration"] else 1.0 / 6
            )  # default value
            if frame_image.mode != "RGBA":
                frame_image = frame_image.convert("RGBA")
            images.append(frame_image)
            # frame_image.save(f"frame_{index}.png")
            self.sequence.add_frame(str(index), duration, False)
            index = index + 1

        self.sequence.compute_aggregated_times()

        self.multi_frame_image = MultiFrameImage(
            name=self.name + "_MultiFrameImage", position=self.position, images=images
        )
        self.sequence.actor = self.multi_frame_image

    def set_from_file(self, file_name: str):
        with Image.open(file_name) as image:
            image.load()
            self.set_from_pil_image(image)

    def get_animations(self) -> list[Animation]:
        return [self.sequence]

    def render(self, canvas: Canvas):
        if self.multi_frame_image:
            self.multi_frame_image.render(canvas)
            self.changes_since_last_render = False

    def needs_render(self):
        return self.multi_frame_image.needs_render() if self.multi_frame_image else False

    def set_position(self, position: tuple[int, int]):
        super().set_position(position)
        if self.multi_frame_image:
            self.multi_frame_image.set_position(position)
