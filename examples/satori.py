"""Satori knot app for lmae.

Renders an animated 2D potential-field / plasma generator (the "Satori knot"
algorithm) to the LED matrix. The algorithm scatters focal points ("knots")
across the canvas, computes a static grayscale field from complex-logarithm
distance/angle math, and animates it via palette cycling (shifting the color
look-up-table offset each frame).

Algorithm spec: examples/Satori_knot_algorithm.md
Palette data:   examples/satori_palette.txt

Architecture:
    SatoriApp (DisplayManagedApp)
      └─ SatoriPattern (StillImage) — owns all satori state + zero-copy buffers

SatoriPattern IS-A lmae StillImage: it inherits render() (alpha_composite into
the stage canvas) and holds a persistent RGBA bytearray with an Image.frombuffer
zero-copy view. Per-frame work mutates the buffer in place — no allocation.
"""

import math
import os
import random
import time
from array import array

from PIL import Image

from lmae import app_runner
from lmae.actor import StillImage
from lmae.app import DisplayManagedApp
from lmae.core import Stage


# ---------------------------------------------------------------------------
# C-fidelity helpers
#
# The original algorithm is C code. These helpers reproduce C-specific numeric
# behavior so the output matches the reference implementation.
# ---------------------------------------------------------------------------


def _c_intdiv(a: int, b: int) -> int:
    """C-style integer division: truncates toward zero.

    Python's ``//`` floors (giving -3 for -5//2), whereas C truncates toward
    zero (giving -2 for -5/2). Using ``int(a / b)`` matches C for values
    within float precision, which covers every case in this algorithm.
    """
    return int(a / b)


def _wrap8(val: float) -> int:
    """Wrap a value into 0-255 like a C cast to unsigned char.

    C casts negative integers to unsigned char via modular arithmetic.
    ``(int(val) % 256 + 256) % 256`` reproduces this for any sign.
    """
    return (int(val) % 256 + 256) % 256


# ---------------------------------------------------------------------------
# Knot — a single focal point with random attributes
# ---------------------------------------------------------------------------


class _Knot:
    """One focal point and its per-style random attributes.

    ``__slots__`` keeps per-knot memory small and attribute access fast.
    """

    __slots__ = (
        "x", "y",
        "flowsign", "spinsign", "leafsign", "rayssign", "wavesign",
        "nspokes", "sectors", "frequency", "amplitude", "decay",
    )


# ---------------------------------------------------------------------------
# Palette parsing
# ---------------------------------------------------------------------------

def _parse_palettes(filepath: str) -> dict[str, list[tuple[int, int, int]]]:
    """Parse a palette file.

    Expected format (one palette per line)::

        Name: #rrggbb #rrggbb ...

    Lines beginning with ``#`` are comments; blank lines are skipped.
    The name is everything before the first colon (so names may contain
    whitespace). Color count is implicit — just count the hex tokens.
    """
    palettes: dict[str, list[tuple[int, int, int]]] = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, sep, rest = line.partition(":")
            if not sep:
                continue
            name = name.strip()
            colors: list[tuple[int, int, int]] = []
            for token in rest.split():
                if len(token) == 7 and token.startswith("#"):
                    c = int(token[1:], 16)
                    colors.append(((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF))
            if name and colors:
                palettes[name] = colors
    return palettes


# The five rendering styles. style1/style2 are chosen from this set.
_ALL_STYLES = ("flow", "wave", "spin", "leaf", "rays")


# ---------------------------------------------------------------------------
# SatoriPattern — the drawing as a StillImage subclass
# ---------------------------------------------------------------------------


class SatoriPattern(StillImage):
    """A Satori knot drawing rendered as a StillImage with a zero-copy buffer.

    Subclasses StillImage to inherit ``render()`` (alpha-composite into the
    stage canvas) and the ``image``/``position``/visibility machinery.

    Holds a persistent ``bytearray`` RGBA buffer with an ``Image.frombuffer``
    zero-copy view. Per-frame palette cycling mutates the buffer in place and
    sets ``changes_since_last_render = True`` — the inherited ``render()``
    then composites the updated pixels into the stage canvas. Steady-state
    per-frame allocation is zero.

    The grayscale field and color table are recomputed only on regeneration
    (every ``refresh_time`` seconds), not per frame.
    """

    def __init__(
        self,
        name: str = "SatoriPattern",
        width: int = 64,
        height: int = 32,
        num_knots: int = 3,
        style1: str = "",
        style2: str = "",
        randomize_palette: bool = True,
        stripes: bool = False,
        palette_name: str = "",
        palette_speed: float = 12.0,
        zoom: float = 1.1,
        seed: int = -1,
        palettes: dict[str, list[tuple[int, int, int]]] | None = None,
    ):
        # Store configuration before super().__init__ so regenerate() can use it
        self._width = width
        self._height = height
        self._num_knots = max(1, num_knots)
        self._style1_pref = style1  # "" => random each generation
        self._style2_pref = style2
        self._randomize_palette = randomize_palette
        self._stripes = stripes
        self._palette_name_pref = palette_name  # "" => random each generation
        self._palette_speed = palette_speed
        self._zoom = zoom
        self._palettes = palettes or {}

        # Seeded RNG (reproducible when seed >= 0; OS-entropy when seed < 0)
        self._rng = random.Random(seed) if seed >= 0 else random.Random()

        # --- Persistent buffers (allocated once, reused across all frames) ---
        npix = width * height
        # RGBA buffer: black, fully opaque. Alpha byte stays 255 forever.
        self._rgba_buf = bytearray(bytes([0, 0, 0, 255]) * npix)
        # Grayscale map: 0-255 per pixel, static between regenerations
        self._grayscale: array = array("B", bytes(npix))
        # Color table flattened to raw RGB bytes, duplicated to 512 entries
        # for the palette-cycling optimization (no modulo per pixel).
        self._color_table_flat: bytearray = bytearray(512 * 3)

        # Create the zero-copy PIL image view over the RGBA buffer.
        # This is the single justified Pillow escape-hatch: lmae offers no
        # buffer-backed image primitive, and this is called exactly once per
        # actor lifetime (never per frame). Mutating _rgba_buf updates the
        # image with no allocation.
        image_view = Image.frombuffer("RGBA", (width, height), self._rgba_buf)
        super().__init__(name=name, position=(0, 0), image=image_view)

        # State populated by regenerate()
        self._knots: list[_Knot] = []
        self._leafdiscrete: int = 1
        self._raysdiscrete: int = 1
        self._style1_name: str = ""
        self._style2_name: str = ""
        self._flow_scale: int = 0  # C-style int(100 / num_knots)
        self._wave_scale: int = 0

        # Generate the first drawing
        self.regenerate()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def regenerate(self) -> None:
        """Produce a brand-new drawing.

        Generates new knots, picks styles/palette, computes the static
        grayscale map, builds the color table, and refreshes the RGBA buffer.
        Reuses the existing bytearray / array buffers (no reallocation).
        """
        rng = self._rng
        w, h = self._width, self._height
        zoom = self._zoom

        # --- Generate knots (positions + per-style attributes) ---
        origin_x = 0.5 * (zoom - 1.0) * w
        origin_y = 0.5 * (zoom - 1.0) * h
        knots: list[_Knot] = []
        for _ in range(self._num_knots):
            k = _Knot()
            k.x = zoom * w * rng.uniform(0, 1) - origin_x
            k.y = zoom * h * rng.uniform(0, 1) - origin_y
            k.flowsign = rng.choice((1.0, -1.0))
            k.spinsign = rng.choice((1.0, -1.0))
            k.leafsign = rng.choice((1.0, -1.0))
            k.rayssign = rng.choice((1.0, -1.0))
            k.wavesign = rng.choice((1.0, -1.0))
            k.nspokes = rng.randint(1, 7)
            k.sectors = k.nspokes / (2 * math.pi)
            k.frequency = 6 * rng.uniform(0, 1) + 3
            # 50% chance amplitude is zero
            if rng.random() < 0.5:
                k.amplitude = 0.0
            else:
                k.amplitude = 8 * k.frequency / (k.nspokes * k.nspokes)
            k.decay = 20 + 30 * rng.uniform(0, 1)
            knots.append(k)
        self._knots = knots

        # --- Global style parameters ---
        self._leafdiscrete = 1 + 3 * rng.randint(0, 2)  # {1, 4, 7}
        self._raysdiscrete = 1 + 3 * rng.randint(0, 2)

        # --- Choose styles (preference or random) ---
        self._style1_name = self._pick_style(self._style1_pref)
        self._style2_name = self._pick_style(self._style2_pref)

        # Precompute C-style integer division scales for flow and wave
        self._flow_scale = _c_intdiv(100, self._num_knots)
        self._wave_scale = _c_intdiv(100, self._num_knots)

        # --- Compute the static grayscale map ---
        self._compute_grayscale()

        # --- Build the color table ---
        palette_colors = self._pick_palette()
        self._build_color_table(palette_colors, rng)

        # Refresh the RGBA buffer for the initial frame (offset 0)
        self._refresh_rgba(0)
        self.changes_since_last_render = True

    def update_frame(self, palette_offset: int) -> None:
        """Advance palette cycling and refresh the RGBA buffer in place.

        Called every frame by the app's ``update_view()``. Mutates the buffer
        in place (no allocation) and marks the actor as needing re-render so
        the inherited ``StillImage.render()`` picks up the new pixels.
        """
        self._refresh_rgba(palette_offset)
        self.changes_since_last_render = True

    # ------------------------------------------------------------------
    # Style / palette selection helpers
    # ------------------------------------------------------------------

    def _pick_style(self, preference: str) -> str:
        """Return the preferred style if valid, otherwise a random one."""
        if preference:
            if preference in _ALL_STYLES:
                return preference
            self.logger.warning(
                "Unknown style %r; choosing randomly. Valid: %s",
                preference, ", ".join(_ALL_STYLES),
            )
        return self._rng.choice(_ALL_STYLES)

    def _pick_palette(self) -> list[tuple[int, int, int]]:
        """Return the preferred palette's colors, or a random palette's."""
        if self._palette_name_pref and self._palette_name_pref in self._palettes:
            return self._palettes[self._palette_name_pref]
        if self._palettes:
            return self._rng.choice(list(self._palettes.values()))
        # Fallback if no palettes loaded (shouldn't happen in normal use)
        return [(255, 255, 255), (0, 0, 0)]

    # ------------------------------------------------------------------
    # Grayscale computation (called only on regeneration)
    # ------------------------------------------------------------------

    def _compute_grayscale(self) -> None:
        """Evaluate the chosen styles for every pixel and fill the grayscale map.

        A checkerboard pattern selects style1 for even ``(x+y)`` and style2 for
        odd. The result is stored once and reused for every frame until the
        next regeneration — palette cycling animates the colors, not the math.
        """
        gs = self._grayscale
        w, h = self._width, self._height

        fn_even = getattr(self, f"_eval_{self._style1_name}")
        fn_odd = getattr(self, f"_eval_{self._style2_name}")

        i = 0
        for y in range(h):
            for x in range(w):
                if (x + y) & 1:
                    gs[i] = fn_odd(x, y)
                else:
                    gs[i] = fn_even(x, y)
                i += 1

    # --- The five style evaluation functions ---
    # All follow the spec exactly, including C-specific numeric behavior.

    def _eval_flow(self, x: int, y: int) -> int:
        """Flow: logarithmic electrostatic potential (2D point charges)."""
        val = 0.0
        log = math.log
        for k in self._knots:
            dx = x - k.x
            dy = y - k.y
            if dx == 0 and dy == 0:
                continue  # guard: log(0) would crash in Python
            val += k.flowsign * log(dx * dx + dy * dy)
        val *= self._flow_scale  # C-style integer division scale
        return _wrap8(val)

    def _eval_wave(self, x: int, y: int) -> int:
        """Wave: sinusoidal interference of the logarithmic distance."""
        val = 0.0
        sin = math.sin
        log = math.log
        for k in self._knots:
            dx = x - k.x
            dy = y - k.y
            if dx == 0 and dy == 0:
                continue
            val += k.wavesign * sin(1.5 * log(dx * dx + dy * dy))
        val *= self._wave_scale
        return _wrap8(val)

    def _eval_spin(self, x: int, y: int) -> int:
        """Spin: angular slicing with exponential-decay waviness."""
        val = 0.0
        sqrt = math.sqrt
        atan2 = math.atan2
        sin = math.sin
        exp = math.exp
        fmod = math.fmod  # C fmod: result has sign of dividend (NOT Python %)
        for k in self._knots:
            dx = x - k.x
            dy = y - k.y
            r = sqrt(dx * dx + dy * dy)
            a = 0.0 if r == 0 else atan2(dy, dx)
            a += k.amplitude * k.sectors * sin(r / k.frequency) * exp(-r / k.decay)
            a = fmod(a * k.sectors, 1.0)
            val += k.spinsign * a
        return _wrap8(256 * val)

    def _eval_leaf(self, x: int, y: int) -> int:
        """Leaf: ratio of axis offsets with discrete color quantization."""
        val = 0.0
        ld = self._leafdiscrete
        for k in self._knots:
            dx = x - k.x
            dy = y - k.y
            adx = abs(dx)
            ady = abs(dy)
            if adx >= ady:
                big, small = adx, ady
            else:
                big, small = ady, adx
            if big == 0:
                a = 0.0
            else:
                ratio = small / big
                a = k.leafsign * 75.0 * ratio * ratio
            # Quantize: C integer division then multiply back
            val += _c_intdiv(int(a), ld) * ld
        return _wrap8(val)

    def _eval_rays(self, x: int, y: int) -> int:
        """Rays: identical math to leaf but uses rays-sign/discrete."""
        val = 0.0
        rd = self._raysdiscrete
        for k in self._knots:
            dx = x - k.x
            dy = y - k.y
            adx = abs(dx)
            ady = abs(dy)
            if adx >= ady:
                big, small = adx, ady
            else:
                big, small = ady, adx
            if big == 0:
                a = 0.0
            else:
                ratio = small / big
                a = k.rayssign * 75.0 * ratio * ratio
            val += _c_intdiv(int(a), rd) * rd
        return _wrap8(val)

    # ------------------------------------------------------------------
    # Color table construction (called only on regeneration)
    # ------------------------------------------------------------------

    def _build_color_table(
        self,
        key_colors: list[tuple[int, int, int]],
        rng: random.Random,
    ) -> None:
        """Build the 512-entry color table (256 entries duplicated to 512).

        Follows the spec's ``get_colortable()`` exactly: determine band count,
        fill band key colors (optionally striped/randomized), linear-blend each
        band across its slice of the 256 slots, then duplicate indices 0-255
        into 256-511 for the palette-cycling lookup optimization.

        Writes into the persistent ``_color_table_flat`` bytearray in place.
        """
        ncolors = len(key_colors)
        randomize = self._randomize_palette
        stripes = self._stripes

        # A. Determine the number of gradient bands
        if not randomize:
            nsteps = ncolors
        else:
            nsteps = rng.randint(3, 5) if stripes else rng.randint(5, 10)
        if stripes:
            nsteps *= 2  # make room for black bands between colors

        # B. Select the key color for each band
        band_colors: list[tuple[int, int, int]] = [(0, 0, 0)] * nsteps
        for ii in range(nsteps):
            if stripes and (ii % 2 == 1):
                band_colors[ii] = (0, 0, 0)  # black stripe
            elif randomize:
                band_colors[ii] = rng.choice(key_colors)  # random, with replacement
            else:
                # Sequential palette colors (skip black-stripe slots)
                idx = ii // 2 if stripes else ii
                band_colors[ii] = key_colors[idx % ncolors]

        # C. Blend each band into its slice of the 256-slot table
        ctable: list[tuple[int, int, int]] = [(0, 0, 0)] * 256
        inv_256 = nsteps / 256.0
        for ii in range(nsteps):
            sr, sg, sb = band_colors[ii]
            er, eg, eb = band_colors[(ii + 1) % nsteps]  # wrap for seamless loop
            band_start = (ii * 256) // nsteps
            band_end = ((ii + 1) * 256) // nsteps
            for idx in range(band_start, band_end):
                t = inv_256 * (idx - band_start)
                omt = 1.0 - t
                # C rounds via add-0.5-and-cast; int() truncates toward zero
                r = int(sr * omt + er * t + 0.5)
                g = int(sg * omt + eg * t + 0.5)
                b = int(sb * omt + eb * t + 0.5)
                ctable[idx] = (r, g, b)

        # D. Flatten into the persistent 512x3 bytearray (duplicated)
        # table[i+256] == table[i] so palette cycling can read g+offset
        # directly (max index 255+255=510 < 512) without a modulo.
        flat = self._color_table_flat
        for i in range(256):
            r, g, b = ctable[i]
            base = i * 3
            flat[base] = r
            flat[base + 1] = g
            flat[base + 2] = b
            dup = (i + 256) * 3
            flat[dup] = r
            flat[dup + 1] = g
            flat[dup + 2] = b

    # ------------------------------------------------------------------
    # Per-frame buffer refresh (zero allocation)
    # ------------------------------------------------------------------

    def _refresh_rgba(self, offset: int) -> None:
        """Write palette-cycled colors into the RGBA buffer in place.

        For each pixel: look up ``(grayscale + offset)`` in the color table
        and write the RGB bytes. Alpha byte stays at 255 (set once at init).
        The color table is duplicated to 512 entries, so ``g + offset``
        (max 255+255=510) never overflows — no per-pixel modulo needed.
        """
        gs = self._grayscale
        ct = self._color_table_flat
        buf = self._rgba_buf
        n = len(gs)
        for i in range(n):
            ci = (gs[i] + offset) * 3
            j = i << 2
            buf[j] = ct[ci]
            buf[j + 1] = ct[ci + 1]
            buf[j + 2] = ct[ci + 2]


# ---------------------------------------------------------------------------
# SatoriApp — lifecycle, frame loop, regeneration
# ---------------------------------------------------------------------------


class SatoriApp(DisplayManagedApp):
    """lmae app that renders an animated Satori knot plasma to the LED matrix.

    All constructor arguments are simple types (int / float / bool / str) with
    plain-value sentinels, making the constructor directly drivable by a
    web-configuration framework:

    - ``""`` for style/palette names means **random per generation**.
    - ``seed = -1`` means **nondeterministic**; ``>= 0`` is reproducible.
    - ``brightness = 0`` means **wall-clock dimming**; ``1-100`` is a fixed override.
    """

    def __init__(
        self,
        width: int = 64,
        height: int = 32,
        num_knots: int = 3,
        style1: str = "",
        style2: str = "",
        randomize_palette: bool = True,
        stripes: bool = False,
        palette_name: str = "",
        palette_speed: float = 24.0,
        zoom: float = 1.1,
        seed: int = -1,
        palette_file: str = "satori_palette.txt",
        regenerate: bool = True,
        refresh_time: int = 120,
        max_frame_rate: int = 30,
        daytime_brightness: int = 100,
        nighttime_brightness: int = 60,
        brightness: int = 0,
        resource_path: str = "",
    ):
        super().__init__(refresh_time=refresh_time, max_frame_rate=max_frame_rate)
        self._width = width
        self._height = height
        self._num_knots = num_knots
        self._style1 = style1
        self._style2 = style2
        self._randomize_palette = randomize_palette
        self._stripes = stripes
        self._palette_name = palette_name
        self._palette_speed = palette_speed
        self._zoom = zoom
        self._seed = seed
        self._do_regenerate = regenerate
        self._daytime_brightness = max(1, min(100, daytime_brightness))
        self._nighttime_brightness = max(1, min(100, nighttime_brightness))
        # 0 = wall-clock dimming; 1-100 = fixed override (skips the clock)
        self._fixed_brightness = max(0, min(100, brightness))
        self._current_brightness: int = -1  # sentinel: not yet applied
        self._resource_path = resource_path

        # Parse palettes once at construction (reused across all generations)
        palette_path = (
            os.path.join(resource_path, palette_file) if resource_path else palette_file
        )
        self._palettes = _parse_palettes(palette_path)

        # The pattern actor — created once in prepare(), reused on re-prepare
        self._pattern: SatoriPattern | None = None

        # Timing (reset in prepare)
        self._run_start: float = 0.0
        self._last_gen: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def prepare(self) -> None:
        """Build the stage and pattern actor.

        Idempotent: on re-prepare (after stop/restart) the existing stage and
        pattern are reused — buffers are kept, not reallocated. Only the
        timing clock is reset.
        """
        # Create the stage with the correct canvas size (DisplayManagedApp
        # defaults to 64x32; we honor the constructor's width/height).
        if not self.stage:
            self.stage = Stage(
                name=f"{self.__class__.__name__}-Stage",
                size=(self._width, self._height),
                matrix=self.matrix,
                matrix_options=self.matrix_options,
            )
        else:
            self.stage.blank_canvas()

        # Create the pattern actor once
        if self._pattern is None:
            self._pattern = SatoriPattern(
                width=self._width,
                height=self._height,
                num_knots=self._num_knots,
                style1=self._style1,
                style2=self._style2,
                randomize_palette=self._randomize_palette,
                stripes=self._stripes,
                palette_name=self._palette_name,
                palette_speed=self._palette_speed,
                zoom=self._zoom,
                seed=self._seed,
                palettes=self._palettes,
            )
            self.stage.actors.append(self._pattern)

        # Reset the timing clock
        self._run_start = time.perf_counter()
        self._last_gen = self._run_start
        # Force brightness re-application on (re-)start
        self._current_brightness = -1

    def _compute_brightness(self) -> int:
        """Return the target matrix brightness (1-100).

        When ``brightness`` was set to a fixed value (1-100), that value is
        returned regardless of time. Otherwise a wall-clock dimming schedule
        is used::

            05:00-06:00  gradual brightening (night -> day)
            06:00-21:00  full daytime brightness
            21:00-22:00  gradual dimming (day -> night)
            22:00-05:00  full nighttime brightness
        """
        if self._fixed_brightness > 0:
            return self._fixed_brightness

        now = time.localtime()
        secs = now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec

        dawn_start = 5 * 3600   # 05:00
        dawn_end = 6 * 3600     # 06:00
        dusk_start = 21 * 3600  # 21:00
        dusk_end = 22 * 3600    # 22:00
        day = self._daytime_brightness
        night = self._nighttime_brightness

        if secs < dawn_start:
            return night
        if secs < dawn_end:
            frac = (secs - dawn_start) / (dawn_end - dawn_start)
            return round(night + (day - night) * frac)
        if secs < dusk_start:
            return day
        if secs < dusk_end:
            frac = (secs - dusk_start) / (dusk_end - dusk_start)
            return round(day + (night - day) * frac)
        return night

    def update_view(self, elapsed_time: float) -> None:
        """Advance palette cycling and optionally regenerate.

        Called every frame by DisplayManagedApp.run(). Uses perf_counter for
        a monotonic clock independent of the framework's elapsed_time (which
        resets each refresh cycle).
        """
        now = time.perf_counter()
        total_elapsed = now - self._run_start

        # Regenerate periodically if enabled
        if self._do_regenerate and (now - self._last_gen) >= self.refresh_time:
            self._pattern.regenerate()
            self._last_gen = now
            self.logger.debug("Regenerated satori drawing")

        # Advance the palette offset and refresh the RGBA buffer in place
        offset = int(total_elapsed * self._palette_speed) % 256
        self._pattern.update_frame(offset)

        # Apply brightness (wall-clock dimming or fixed override).
        # Only writes to the matrix when the value actually changes.
        target = self._compute_brightness()
        if target != self._current_brightness:
            if self.stage and self.stage.matrix:
                self.stage.matrix.brightness = target
            self._current_brightness = target
            self.logger.debug("Brightness set to %d", target)

    @staticmethod
    def get_app_instance() -> "SatoriApp":
        """Return a default instance (lmae convention)."""
        resource_path = os.path.dirname(__file__)
        return SatoriApp(resource_path=resource_path)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app_runner.start_app(SatoriApp.get_app_instance())
