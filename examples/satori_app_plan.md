# Plan: `examples/satori.py` — Satori Knot App for lmae

## 1. Goal

Implement a new lmae app, `examples/satori.py`, that renders the **Satori knot**
algorithm (a 2D potential-field / plasma generator animated via palette cycling)
to the LED matrix. The algorithm spec lives in `examples/Satori_knot_algorithm.md`,
and palette data lives in `examples/satori_palette.txt` (14 palettes, already
present, in a simple `Name: #rrggbb #rrggbb ...` format — CSS-style hex, no
per-line count, no alignment to maintain).

Constraints honored:
- **Prefer lmae components.** Build on `lmae`'s primitives — `DisplayManagedApp`,
  `StillImage`, `Stage`, `Canvas`, `app_runner` — and reach for a third-party
  library (Pillow) directly **only** where lmae offers no equivalent. In
  practice that is a single setup-time `Image.frombuffer` to get a zero-copy,
  buffer-backed image (see §3, §7). No numpy.
- **No new dependencies.** Pure Python + the project's existing libs (Pillow,
  pygame via the virtual matrix).
- **No memory leaks / allocation churn.** Reuse persistent buffers; never
  allocate per frame.
- **Double-buffered rendering.** Compose the full image off-screen, then present
  it in one swap. (The existing `lmae.core.Stage` already does this for us — see
  §7.)
- **Configurable via the constructor**, with sensible defaults; default canvas
  size `64 x 32`.

---

## 2. Files

| File | Action |
|------|--------|
| `examples/satori.py` | **Create.** App class, custom `StillImage` subclass, algorithm + palette logic, `__main__` entrypoint. |
| `examples/satori_palette.txt` | **Read-only.** Already exists; parsed at runtime. |
| `examples/cycle.py` | (Optional, later) register `SatoriApp` in the rotation. **Not part of this task.** |

No changes to `lmae/` library code are required. The Stage/Actor/Canvas/App
primitives already provide everything we need.

---

## 3. Architecture overview

```
SatoriApp (DisplayManagedApp)            <- lifecycle, frame loop, regeneration
  └─ owns one SatoriPattern (StillImage) <- IS-A lmae StillImage; owns Satori state + buffers
       ├─ grayscale map (static per generation)   array('B'), w*h
       ├─ color table (256 -> duplicated to 512)  list[(r,g,b)]
       ├─ RGBA frame buffer (reused every frame)  bytearray w*h*4
       └─ PIL image view over that buffer         Image.frombuffer (zero-copy), held as StillImage.image
  └─ stage (Stage)                        <- double-buffered canvas -> matrix
```

The app owns a single actor (`SatoriPattern`) which is the whole frame. Each
frame the app advances the palette offset and asks the actor to refresh its
buffer; the Stage then composes the canvas and swaps on VSync.

**Reuse lmae components first.** `SatoriPattern` **subclasses `StillImage`**
and inherits its `render()` (the `canvas.image.alpha_composite(self.image, ...)`
path) and its `image`/`position`/visibility machinery. We do **not** override
`render()` and we do **not** call `StillImage.set_from_image()` per frame (that
swaps in/`.convert()`s a new PIL image each frame → allocation churn and GC
pressure, exactly what `examples/cycle.py`'s `tracemalloc` checks guard
against). Instead:

- At construction, build **one** persistent RGBA image via `Image.frombuffer`
  over a reusable `bytearray` and pass it to `StillImage.__init__(image=...)`.
  `Image.frombuffer` is the one justified escape hatch — lmae offers no
  zero-copy, buffer-backed image, and it is used exactly once per actor
  lifetime (not per frame).
- Each frame: mutate the bytearray in place, then set the inherited
  `self.changes_since_last_render = True` so the Stage re-renders. StillImage's
  inherited `render()` then alpha-composites the same (now-updated) image into
  the stage canvas.

Result: full reuse of lmae's `StillImage` + `Stage` + `Canvas` + `App` pipeline,
zero per-frame image allocation, and the only direct third-party touch is the
single `Image.frombuffer` at setup.

---

## 4. Public API (constructor + defaults)

**All constructor arguments are simple types** (`int`, `float`, `bool`, `str`)
— no dataclass, no tuple, no `Optional`/`None`. This keeps the constructor
directly drivable by a forthcoming web-configuration framework. Sentinels use
plain values of the same type:
- `""` (empty string) for `style1`/`style2`/`palette_name` means **random per
  generation**.
- `seed = -1` means **nondeterministic** (RNG seeded from OS entropy); any
  value `>= 0` is an explicit, reproducible seed.
- Canvas size is two ints (`width`, `height`) rather than a tuple.

### `SatoriApp` constructor

```python
class SatoriApp(DisplayManagedApp):
    def __init__(
        self,
        width: int = 64,                # canvas width in pixels
        height: int = 32,               # canvas height in pixels
        num_knots: int = 3,             # focal points scattered on the canvas
        style1: str = "",               # "" => random each generation
        style2: str = "",               # "" => random each generation
                                        # choices: "flow","wave","spin","leaf","rays"
        randomize_palette: bool = True, # algorithm's `randomize` flag
        stripes: bool = False,          # algorithm's `stripes` flag (black bands)
        palette_name: str = "",         # "" => random palette each generation
        palette_speed: float = 12.0,# palette shift speed (steps per second)
        zoom: float = 1.1,              # knot placement zoom (from spec)
        seed: int = -1,                 # -1 => nondeterministic; >=0 => reproducible
        palette_file: str = "satori_palette.txt",
        regenerate: bool = True,        # periodically produce a brand-new drawing
        refresh_time: int = 120,        # seconds between regenerations
        max_frame_rate: int = 30,       # animation fps cap
        resource_path: str = "",        # dir containing palette_file
    ):
```

Notes:
- `width`/`height` are combined into a `(width, height)` tuple only when
  forwarding to the `Stage`/`Canvas` internally; the public surface stays
  simple-typed.
- `refresh_time` is reused for the regeneration cadence, matching the existing
  `DisplayManagedApp` semantics (see §7).
- `get_app_instance()` static method (per lmae convention) builds an instance
  with `resource_path = os.path.dirname(__file__)`.

---

## 5. Algorithm implementation details

All math follows `Satori_knot_algorithm.md`. Critical C-specific behaviors
(§"Critical Implementation Details" of the spec) are reproduced exactly.

### 5.1 Knot generation

One `Knot` per `num_knots`, using a seeded `random.Random` instance (stored on
the actor so re-seeding is deterministic):

- `x = zoom * width  * U(0,1) - origin_x`, with `origin_x = 0.5*(zoom-1)*width`
  (same for `y`).
- Signs `flowsign/spinsign/leafsign/rayssign/wavesign` ∈ {+1, -1}.
- `nspokes` ∈ [1, 7]; `sectors = nspokes / (2*pi)`.
- `frequency = 6*U(0,1) + 3`.
- `amplitude = 0` w.p. 0.5, else `8 * frequency / (nspokes**2)`.
- `decay = 20 + 30*U(0,1)`.

Global:
- `leafdiscrete = 1 + 3*randint(0,2)` → {1,4,7}; `raysdiscrete` likewise.

### 5.2 The five styles (per pixel `(x, y)`)

`dx = x - knot.x`, `dy = y - knot.y`. Style chosen by checkerboard:
`(x + y) % 2 == 0 → style1 else style2`.

Helpers to match C exactly:
- **C-style integer division / truncation toward zero:** a `_c_intdiv(a, b)`
  helper using `int(a / b)` (Python's `int()` truncates toward zero, unlike
  `//`). Used for `100 // num_knots` in flow/wave and the `(int(a)/discrete)*discrete`
  quantization in leaf/rays.
- **`fmod` with sign of dividend:** use `math.fmod` (NOT Python `%`).
- **8-bit wrap:** `final = (int(val) % 256 + 256) % 256` (handles negatives).

Styles:
- **flow:** `Σ flowsign * log(dx²+dy²)`; guard `dx==0 and dy==0` (skip → avoids
  `log(0)`). Multiply by `_c_intdiv(100, num_knots)`.
- **wave:** `Σ wavesign * sin(1.5 * log(dx²+dy²))`; same log guard; same scale.
- **spin:** per knot: `r=sqrt(dx²+dy²)`; `a = 0 if r==0 else atan2(dy,dx)`;
  `a += amplitude*sectors*sin(r/frequency)*exp(-r/decay)`;
  `a = fmod(a*sectors, 1.0)`; `val += spinsign*a`; return `int(256*val) % 256`.
- **leaf:** `big=max(|dx|,|dy|)`, `small=min(...)`; `a=0 if big==0 else
  leafsign*75*(small/big)**2`; `val += _c_intdiv(int(a), leafdiscrete)*leafdiscrete`.
- **rays:** identical to leaf but uses `rayssign` and `raysdiscrete`.

### 5.3 Static grayscale map (computed once per generation)

A flat `array('B')` of length `width*height`. For each pixel, evaluate the
selected style (checkerboard picks style1 or style2) and store the wrapped 0–255
value. This map is **never recomputed per frame** — that is the whole point of
palette cycling.

A small performance note for pure Python: the inner per-knot work is the cost.
We pre-extract knot fields into local variables inside the per-style loops and
keep the per-pixel loop tight. At 64x32 with ~5 knots this is a few ms and runs
only on regeneration, not per frame.

---

## 6. Palette system + color table

### 6.1 Parsing `satori_palette.txt`

Format per line: `Name: #rrggbb #rrggbb ...` (one palette per line; lines
beginning with `#` are comments; blank lines skipped). **Separate the name
from the colors on the first colon** via `name, _, rest = line.partition(":")`
so palette names may contain whitespace (e.g. `Cold Blue: ...`). Then
`tokens = rest.split()` gives the color tokens; parse each as 6-digit hex via
`int(token[1:], 16)`, then split with bitmasks: `R=(c>>16)&0xff`,
`G=(c>>8)&0xff`, `B=c&0xff`. The color count per palette is implicit (just
count the tokens) — no `N` field to keep in sync.
Parsed once at construction into a `dict[str, list[(r,g,b)]]`; reused across
generations (no re-reading the file).

### 6.2 Building the 256-entry color table (duplicated to 512)

Implement `get_colortable(key_colors, randomize, stripes, rng)` exactly per
spec §"Generating the 256-Entry Color Table":

1. **Bands (`nsteps`):**
   - `randomize=False` → `nsteps = len(key_colors)`.
   - `randomize=True` → `nsteps = rng.randint(5,10)` (or `3..5` if `stripes`).
   - if `stripes` → `nsteps *= 2`.
2. **Fill `colors[nsteps]`:** if `stripes`, odd indices = black `(0,0,0)`; even
   (or all) indices = random palette color (with replacement) if `randomize`,
   else sequential palette colors (cycling).
3. **Blend into 256 slots:** for band `ii`, start=`colors[ii]`,
   end=`colors[(ii+1)%nsteps]`; for each `idx` in the band's slice:
   `t = (nsteps/256.0)*(idx - (ii*256//nsteps))`; lerp with rounding
   (`round(start*(1-t) + end*t)`, using `int(x+0.5)` to mimic the C cast).
4. **Duplicate to 512:** copy indices 0..255 into 256..511 (the palette-cycling
   optimization). Store the table as a flat `list[(r,g,b)]` of length 512,
   regenerated **only** when the palette/regeneration changes.

### 6.3 Per-frame color lookup

Given frame offset `f` (an int in [0,255]) and grayscale value `g`:
`rgb = table[g + f]` — valid because `g+f ≤ 255+255 = 510 < 512`, so the
duplication removes the need for a modulo per pixel. Advance `f` over time from
`palette_speed`.

---

## 7. Rendering pipeline (double buffering)

This requirement is satisfied by the existing framework — no custom swap code:

1. `SatoriApp(DisplayManagedApp).run()` calls `update_view()` then
   `stage.render_frame()` each frame (see `lmae/app.py:216`).
2. `Stage.render_frame()` (`lmae/core.py:337`):
   `update_actors()` → if needed: `prepare_frame()` (blanks the canvas),
   `render_actors()` (every actor composes into the **same off-screen canvas**),
   `display_frame()`.
3. `Stage.display_frame()` does `double_buffer.SetImage(canvas.image.convert("RGB"))`
   then `matrix.SwapOnVSync(double_buffer)` — a single atomic present. No
   partial frame is ever shown.

So our only job is: make `SatoriPattern` present a fully-composed frame into
the stage canvas. Because `SatoriPattern` **is a `StillImage`**, it already
does this — its inherited `render()` alpha-composites `self.image` into the
canvas. The Stage handles the rest of the double buffering.

### `SatoriPattern` buffers + per-frame update — zero-allocation

The actor holds, created once at construction (and resized only if the canvas
size ever changes):
- `self._rgba_buf`: `bytearray(width*height*4)` — alpha always 255.
- `self.image`: the inherited `StillImage.image`, set once via
  `Image.frombuffer("RGBA", (width,height), self._rgba_buf)` — a **zero-copy
  view** over the bytearray; mutating the bytearray updates `self.image` with
  no allocation. (We never call `set_from_image`, so no per-frame
  `.convert('RGBA')` churn.)
- `self._grayscale`: `array('B')` length w*h.

Per-frame update (a method like `update_frame(elapsed)`; not an override of
`render`):
1. Advance offset: `offset = int(elapsed * palette_speed) % 256`.
2. Refresh buffer in place: for each pixel index `i`,
   `g = grayscale[i]; r,g_,b = table[g+offset]` (offset clamped so `g+offset≤511`);
   write `(r,g_,b,255)` into `_rgba_buf[i*4:(i+1)*4]`.
   (Use a local alias to `self._rgba_buf` and slice assignment for speed; keep
   the alpha byte constant.)
3. Set the inherited `self.changes_since_last_render = True` so the Stage knows
   to re-render this frame.

The Stage then calls the inherited `StillImage.render(canvas)`, which does
`canvas.image.alpha_composite(self.image, dest=(0,0))` — reads our updated
image, writes into the persistent stage canvas. **No new images created.**

The per-frame work is just one pass of 2048 table lookups + buffer writes plus
the inherited `alpha_composite`. No PIL `Image.new`, no `convert` (our image is
already RGBA), no `set_from_image`. Steady-state allocation ≈ 0.

---

## 8. App lifecycle & regeneration

`SatoriApp` uses `DisplayManagedApp`, so it gets the frame loop for free. We
override:

- `prepare()`: build the `Stage` (via `super()`), instantiate `SatoriPattern`,
  add it to the stage, and trigger the **first generation** (knots + grayscale
  map + color table). Idempotent on re-`prepare` (guard like the other apps).
- `update_view(elapsed_time)`:
  - Track total elapsed for palette cycling; pass the current offset to the
    actor (or let the actor track its own clock from `elapsed_time`).
  - If `regenerate` and `elapsed_time >= refresh_time` since last generation:
    regenerate (new knots, new grayscale map, new color table, reset offset),
    and reset the generation clock. Logged at DEBUG.
  - Always set `stage.needs_render = True` so the palette cycle animates every
    frame (the pattern genuinely changes each frame).
- `stop()`: call `super().stop()`; clear generation clock; the actor keeps its
  buffers (reused if restarted). No teardown of buffers needed.
- `get_app_instance()`: `resource_path = os.path.dirname(__file__)`, return
  `SatoriApp(resource_path=resource_path)`.

Regeneration reuses the existing `array`/`bytearray` buffers (assign into them
rather than reallocating) to keep memory stable across the long-running cycle.

---

## 9. Memory-safety checklist (explicit, per the project's emphasis)

- [x] **One** RGBA buffer (`bytearray`) + **one** `Image.frombuffer` view (held
      as the inherited `StillImage.image`), both reused every frame. Never
      `Image.new(...)` per frame and never `set_from_image(...)` per frame.
- [x] Rendering reuses lmae's `StillImage.render()` / `Stage` / `Canvas`; the
      only direct third-party touch is the single setup-time `Image.frombuffer`
      (justified: lmae has no buffer-backed image primitive).
- [x] **One** grayscale `array('B')`, reused across generations.
- [x] **One** color table `list`, replaced (not appended) only on palette change.
- [x] Actor never holds references to stage-owned canvas beyond a render call.
- [x] No global/module-level mutable state (unlike `world_clock.py`'s
      `_day_night_mask_image`, which we intentionally avoid).
- [x] `random.Random` instance owned by the actor (no global RNG mutation).
- [x] On regeneration we overwrite buffer contents in place; the bytearray
      length is constant for a fixed canvas size, so no growth/realloc.
- [x] `stop()` does not drop buffers, so a restart (as in `cycle.py`) reuses
      them rather than leaking the old ones and allocating new.
- [x] Verify with the project's existing tooling: run under `examples/cycle.py`
      style `tracemalloc`/`gc` and confirm top allocations stay flat across many
      regenerations (see §11).

---

## 10. Default values summary

| Setting                        | Default                                     |
|--------------------------------|---------------------------------------------|
| `width` / `height`             | 64 / 32                                     |
| `num_knots` | 3 |
| `style1` / `style2`            | `""` → random per generation                |
| `randomize_palette`            | True                                        |
| `stripes`                      | False                                       |
| `palette_name`                 | `""` → random per generation                |
| `palette_speed`            | 12.0                                        |
| `zoom`                         | 1.1                                         |
| `seed`                         | `-1` (nondeterministic; `>=0` reproducible) |
| `regenerate`                   | True                                        |
| `refresh_time` (regen cadence) | 120 s                                       |
| `max_frame_rate`               | 30 fps                                      |

All parameters are simple types (`int`/`float`/`bool`/`str`); see §4.

---

## 11. Verification plan (before declaring done)

1. **Lint/typecheck:** run whatever the repo uses (check for ruff/mypy config;
   `uv run` if present). Confirm clean.
2. **Smoke run (macOS virtual matrix):**
   `uv run python examples/satori.py` — confirm the pygame window shows an
   animated, flowing plasma that changes palette colors over time and
   regenerates a new pattern periodically.
3. **Determinism check:** construct two `SatoriApp` with the same `seed` and
   assert their initial grayscale maps are byte-identical.
4. **C-fidelity spot checks:** tiny unit checks (pure functions, no matrix
   needed) that `_c_intdiv` truncates toward zero, `fmod` keeps sign, 8-bit wrap
   handles negatives, and the color table is length 512 with `t[i+256]==t[i]`.
5. **Memory stability:** drive the actor through ~200 generations + frames in a
   loop (no matrix) under `tracemalloc`; assert the top allocation count and the
   process RSS do not grow unboundedly across regenerations.
6. **No-leak re-entry:** simulate `cycle.py`-style `stop()`→`prepare()`→`run()`
   twice and confirm no additional buffers are allocated on the second run
   (buffers reused).

If any check cannot be run in this environment, say so explicitly and why.

---

## 12. Open questions

None remaining — all architecture-affecting decisions were resolved up front
(pure-Python, periodic regeneration, palette file at
`examples/satori_palette.txt`, constructor-configurable styles random by
default). Any minor choices encountered during implementation (e.g. exact lerp
rounding helper) will follow the spec verbatim and be documented in code
comments.
