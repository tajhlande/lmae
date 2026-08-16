# Memory-Efficient, Re-Runnable lmae Apps

This guide explains how to write lmae apps that can run for weeks inside a
long-lived process without slowly leaking memory. It is written for
both human app creators and agent software; the rules are stated so they can
be checked mechanically.

**Terminology.** An app is *re-runnable* when it can be run
(`prepare()` → `run()`), stopped, and run again any number of times within
the same long-lived process, and still (a) behaves correctly and (b) consumes
no additional memory. 

Reference examples: 
- `examples/weather_app.py` (the canonical well-behaved app)
- `examples/satori.py` (which needed a fix for violating Rule 3).

## Why this matters: the app lifecycle

Apps are not run once and discarded. Sequence runners such as
`examples/cycle.py` create app instances **once**, then repeatedly execute:

```
app.prepare()  ->  asyncio task app.run()  ->  app.stop()  ->  (repeat forever)
```

all inside a single Python process that can stay up for weeks on a Raspberry Pi
with limited RAM. Two consequences:

1. Anything allocated per run/refresh cycle and **retained** by the runtime
   accumulates forever — the Pi slowly fills swap and the apps will fail.
2. Anything destroyed in `stop()` must be cheaply rebuildable or, better,
   kept and reused by the next `prepare()`.

A leak of a few KB per minute is invisible in testing and fatal in
production. The library itself (`lmae/`) is audited for this; app authors must
be wise in implementing apps to avoid memory problems creeping in.

## Guiding rules

### Rule 1: Build everything durably once, in `__init__`

Construct actors, load fonts, load pre-baked images, and parse input data 
files in the app constructor, not in `prepare()` or `run()`. Constructors run 
exactly once per instance, regardless of how many run/stop cycles the app 
survives.

Example: `examples/weather_app.py` builds every actor (labels, sprites,
carousel, background) in `__init__` and loads all images/fonts there;
`prepare()` only wires them to the stage.

```python
def __init__(self, ...):
    self.font = ImageFont.truetype(...)          # once
    self.label = Text(font=self.font, ...)       # once
    self.image = Image.open(...).convert("RGBA") # once
```

### Rule 2: Make `prepare()` idempotent

`prepare()` is called before **every** run. Guard resource creation and only
reset transient state (clocks, flags, animation scheduling):

```python
def prepare(self) -> None:
    super().prepare()
    if not self.stage:
        self.stage = Stage(...)            # first time only
    else:
        self.stage.blank_canvas()          # reuse the stage

    if self.my_actor is None:              # first time only
        self.my_actor = MyActor(...)
        self.stage.actors.append(self.my_actor)

    self._run_start = time.perf_counter()  # reset every time
```

The weather app's pattern — clear the stage lists and re-append the *same*
actor/animation instances — is equally valid:

```python
stage.animations.clear()
stage.actors.clear()
actors.extend([self.label_a, self.label_b, ...])  # same instances, re-added
```

### Rule 3: Give re-created LMAE object instances like animations FIXED names 

This is the rule most easily violated, because the leak is invisible in the
app's own objects.

**The mechanism.** Every `LMAEObject` constructor without an
explicit `name=` gets a unique sequential name from `_get_sequential_name`
(`lmae/core.py` — e.g. `HueFade_183`, `Sequence_47`). Every
`LMAEObject.__init__` then calls `logging.getLogger(name)` — and Python's
logging registry (`logging.Logger.manager.loggerDict`) retains every logger
**forever**. The animation objects themselves are garbage-collected when
finished, but their loggers never are.

So any code path that re-creates actors or animations on a schedule — scrolling 
text rebuilt on every data refresh, an overlay rebuilt on every regeneration —
leaks one permanent logger (plus name string and bookkeeping) per unnamed
object, per rebuild.

**Case study.** `examples/satori.py` rebuilt its palette-name overlay (about
11 animation objects) on every regeneration. In the deployment that hit swap
exhaustion, the app ran in a 30-second sequence (10 seconds world clock,
20 seconds satori, repeat), regenerating — and rebuilding the overlay — once
per 20-second satori run. None of the animation objects had names
declared. At two rebuilds per minute, that is roughly 1,300 permanent loggers
per hour, ~32,000/day, ~220,000/week — on the order of 100 MB of logger
objects, name strings, and registry bookkeeping accumulated over a week.
That slow, monotonic RSS creep matched the week-scale swap exhaustion on the
Pi. The fix: fixed names (`"Satori-overlay-sequence"`,
`"Satori-overlay-fade-in-text"`, ...), so `getLogger()` returns the same
logger every time and nothing accumulates.

**The rule.** Whenever you construct an `Animation` (or any `LMAEObject`)
that may be constructed more than once over the app's lifetime, pass an
explicit, stable `name=`. Use a consistent prefix tied to the feature, as
the weather app does:

```python
pause_1 = Still(name="Condition-pause-1", actor=self.label, ...)
scroll  = StraightMove(name="Condition-scroll-left", actor=self.label, ...)
seq     = Sequence(name="Condition-scroll-sequence", actor=self.label, ...)
```

Animations created exactly once in `__init__` are safe either way, but a
fixed name is still good practice (it also makes logs readable).

### Rule 4: Reuse buffers; never allocate per frame

`update_view()` and render paths run at frame rate (up to ~30-120 fps).
Steady-state per-frame work must mutate existing buffers rather than
allocate.

The strongest pattern (from `examples/satori.py`): allocate `bytearray` /
`array` buffers once, wrap them in a zero-copy PIL view once, then only ever
assign into them:

```python
self._rgba_buf = bytearray(width * height * 4)          # once
self._image = Image.frombuffer("RGBA", (w, h), self._rgba_buf)  # once, zero-copy

def update_frame(self):
    for i, v in enumerate(values):        # per frame
        self._rgba_buf[i] = v             # in-place mutation, no allocation
```

Notes:

- Library actors already follow this: `Text` prerender reuses a grow-only
  image (bounded by the longest string you set); `Stage` reuses one `Canvas`.
- Double buffering can be used with two prepared canvases to avoid a visible
  building of artifacts onto a stage if desired. In that case, use
  two `Canvas` objects.
- Transient small allocations (tuples, temporary lists) are fine — they are
  garbage-collected promptly. The danger is objects **retained by the
  runtime** (loggers, caches, stage lists that only grow).

### Rule 5: `stop()` must not drop resources

`stop()` just sets `running = False`. Do not close, clear, or null out
buffers, actors, images, fonts, or the stage — the next `prepare()` (and in
`cycle.py` there will be one) should find them intact and reuse them. Reset
*timing* state, not *resources*.

```python
def stop(self) -> None:
    super().stop()   # sets running = False; that's all
```

### Rule 6: Clear before re-adding stage animations

If you construct new animations for an actor (see Rule 3), remove the 
old ones so they can be collected:

```python
stage.clear_animations_for(self.label)   # drop previous overlay/scroll
stage.add_animation(new_sequence)
```

The stage itself prunes finished non-repeating animations after each frame
(`Stage.post_render`), but long-running or repeating animations persist
until you clear them explicitly.

### Rule 7: Decide whether your app should resume its view or start fresh when re-run

It's up to the app author to decide the correct behavior when an app is
"resumed" by calling `run()` again after `stop()`.  You may wish to start the
app over from the beginning, or resume the previous display.  In either case, 
re-use existing objects as described in Rule 1.

## Checklist for a new app (and for reviewing one)

- [ ] All actors, fonts, images, parsed data created in `__init__`, once.
- [ ] `prepare()` guarded with `is None` (or clear-and-re-add) — idempotent,
      safe to call any number of times.
- [ ] Every animation constructed in code that can run more than once has a
      fixed `name=`.
- [ ] No allocations in `update_view()` / render paths beyond small
      transients; pixel buffers allocated once and mutated in place.
- [ ] `stop()` sets the stopped flag only; no teardown of reusable resources.
- [ ] Re-created animations are preceded by `stage.clear_animations_for()`.
- [ ] Verified with a soak test (below).
- [ ] Decide whether the app should resume or restart its view when re-run.

## Soak test snippet

Simulate `cycle.py`-style re-runs and confirm nothing accumulates. The logger
count is the assertion that catches Rule 3 violations:

```python
import logging

def logger_count() -> int:
    return sum(
        1
        for v in logging.Logger.manager.loggerDict.values()
        if isinstance(v, logging.Logger)
    )

app = MyApp()
app.stage = Stage(name="test", size=(64, 32))
app.prepare()

before = logger_count()
for _ in range(500):
    app._recreated_animations_method(...)  # the code path under test
    app.prepare()
delta = logger_count() - before
assert delta <= EXPECTED_FIXED_SET_SIZE, f"logger leak: +{delta}"
```

On a real device, also watch RSS over time (`ps -o rss= -p <pid>`) during an
overnight run; it should be flat after the first few minutes.
