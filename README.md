# LMAE - LED Matrix Animation Engine for RPi and Python

<!--suppress CheckImageSize -->
<img alt="LMAE demo image" height="259" src="doc/images/lmae_demo_image.png" title="LMAE demo image" width="515"/>

A library for building little applications  that can run on a Raspberry Pi and
display interesting things on a LED matrix.
The matrix I have is from Adafruit and it is
[64 x 32, 3mm pitch](https://www.adafruit.com/product/2279).
I am driving it with a Raspberry Pi 3B and a [matrix bonnet](https://www.adafruit.com/product/3211).

## Table of Contents
<!-- TOC -->
* [LMAE - LED Matrix Animation Engine for RPi and Python](#lmae---led-matrix-animation-engine-for-rpi-and-python)
  * [Table of Contents](#table-of-contents)
  * [LMAE Basics](#lmae-basics)
    * [Prerequisites](#prerequisites)
    * [Getting started](#getting-started)
    * [Setting up your development environment to work on this project](#setting-up-your-development-environment-to-work-on-this-project)
    * [Setting up your development environment for a project that uses `lmae` as a package](#setting-up-your-development-environment-for-a-project-that-uses-lmae-as-a-package)
    * [Virtual LED Display](#virtual-led-display)
    * [Library structure](#library-structure)
* [Weather app](#weather-app)
    * [OpenWeather API bookmarks](#openweather-api-bookmarks)
    * [Visual crossings bookmarks](#visual-crossings-bookmarks)
* [Creating new apps](#creating-new-apps)
  * [Important classes](#important-classes)
      * [Core classes](#core-classes)
      * [Actor classes](#actor-classes)
      * [Animation classes](#animation-classes)
      * [Component classes](#component-classes)
  * [App framework](#app-framework)
    * [App classes](#app-classes)
<!-- TOC -->

## LMAE Basics

### Prerequisites

This library is built on top of the RGB LED display driver
written by Henner Zeller, found here: [hzeller/rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix)
You'll need to build that first, as this library depends on it for access to the LED matrix.
In particular, you need to `make install` the python 3 bindings to get all of the needed binaries,
which are not included in this project. The README for that project will explain that
and many other things which are useful to know for getting things working.

On my Pi with the latest version of the library, I also had to follow the guidance to
switch off on-board sound (`dtparam=audio=off` in `/boot/config.txt`)
and blacklist the `snd_bcm2835` kernel module by adding a file `/etc/modprobe.d/blacklist-rgb-matrix.conf`
with the following contents:

    blacklist snd_bcm2835

The alternative, if you don't want to do this, is to disable hardware pin-pulse generation with the command line
option `--led-no-hardware-pulse 1`. This will also let you avoid having to run with `sudo`. See below for more details.

### Getting started
`render_test.py` is an example program that test the basics of the core
library. You should create a virtual environment using `venv`:

    python -m venv venv

Activate your environment:

    source venv/bin/activate

Install the required library modules:

    pip install -r requirements.txt

Run the first example in a virtual LED window on your laptop:

    python examples/render_test.py

If all is successful, you will see a surprise animation demo!
Press "return" on the app console to end the test.

To run on the Raspberry Pi with the real LED matrix hardware,
you need to install the `rgbmatrix` library into the venv environment in development mode, referencing
the path to the python bindings in your copy of the `rpi-rgb-led-matrix`, so after activating your
virtual environment, run something like:

    pip install -e ${PATH_TOPROEJCT}/rpi-rgb-led-matrix/bindings/python

And then run the example like this:

    sudo venv/bin/python examples/render_test.py

The `sudo` is necessary to allow the LED matrix code to run with
the elevated privileges necessary to achieve best GPIO timing performance.
And because `sudo` doesn't use the user's path, the usual means to activating
the virtual environment doesn't work.

### Setting up your development environment to work on this project

The following assumes you want to develop on a Windows or Mac laptop, separate from the RPi.

In order to get your IDE to find the `rgbmatrix` module so all your syntax highlighting
will be nice and clean, you'll need to do one of the following to install the module in
development mode, as it isn't platform-independent and can't be installed from PyPI:

1.  `pip install -e ${PATH_TO_PROJECT}/rpi-rgb-led-matrix/bindings/python` in your IDE's virtual environment.
2.  Add the python bindings path (the same path as what you set in the
    `pip -e` command above) to your IDE's Python `sys.path` or `PYTHONPATH` settings.

Instructions for JetBrains IDEs can be found [here](https://www.jetbrains.com/help/idea/installing-uninstalling-and-reloading-interpreter-paths.html).
Instructions for VSCode can be found [here](https://code.visualstudio.com/docs/python/environments#_environment-variable-definitions-file).
 
### Setting up your development environment for a project that uses `lmae` as a package

First, follow the instructions above to install the `rgbmatrix` module in development mode, 
then do one of the following in the same manner for this project:

1.  `pip install -e ${PATH_TO_PROJECT}/lmae` in your IDE's virtual environment.
2.  Add the python bindings path (the same path as what you set in the
    `pip -e` command above) to your IDE's Python `sys.path` or `PYTHONPATH` settings.
3.  If you're using Poetry, you can run a command like `poetry add --editable ${PATH_TO_PROJECT}/lmae`, or
4.  Edit your `poetry.toml` under the `[tool.poetry.dependencies]` header to include
    `lmae = {path = "${PATH_TO_PROJECT}/lmae", develop = true}`

The packaging for the `lmae` module doesn't include the `rgbmatrix` dependency, so you'll need to include it
in your dependency list.

### Virtual LED Display

To make it easier to develop and iterate apps without having to push every change to the RPi,
running the code on a Windows or Mac computer will trigger
the code to draw to a virtual display window rather than looking for a real
Raspberry Pi LED display. This feature is built with Pygame, hence the dependency on it.

I have only tested this on a Mac, though in theory it should also work in Windows.
It probably will not work in a Linux development environment, because the code is using
the operating system name to manage the implementation class substitution. This might be
fixed in the future, but it works for me now.


### Library structure

The core of the library are classes for basic elements
that you might find in a game engine:
there is a stage and there are actors on the stage,
and animations that modify those actors. To display a scene,
you create a stage, attach a matrix object to it, and
tell it to render a frame.

Actors can decide how to render themselves on the stage.
Some basic actors are provided for still images, moving images, and text rendering.
Actors generally are expected to know their size and position, their current
visibility, whether or not they have been modified in any way that would change
the rendering outcome.  On a stage, actors are rendered in the order that they appear
in the actor list, so the first actor has bottom Z order, the last actor has top Z order,
and so on for the actors in between.

Composite actors are actors that modify the rendering behavior of other actors.
For example, a crop actor limits the rendered visibility of an actor to a rectangular window.

Animations are instructions for modifying an actor – so far,
mainly for changing its position via movement over time.
Animations are designed to be independent of frame rate, so they have a
duration and a destination, and will get there whether that renders in 10
frames or 100 frames.

To make animations happen, they are assigned to an actor and added to the stage,
where they take effect immediately upon the next rendering of the stage.
Animations may be set to repeat once completed.
If they are not set to repeat, they are removed from the stage on completion.

Components are actors that know how to generate their own animations.
This is meant to encapsulate complex animation behavior.

The `lmae.app` module, along with the `lmae.app_runner` module, provide tools for the
construction and execution of apps.



# Weather app

A reasonably complex demo app in included in `weather_app.py`. 
It is a weather conditions display app that relies on the [OpenWeather One Call API](https://openweathermap.org/api/one-call-api)
to get current weather conditions for a given location, specified by
latitude & longitude.

You need to set the following environment variables:

* `OW_API_KEY` - Your OpenWeather API key
* `LATITUDE` - The latitude of the location for which you wish to get weather conditions
* `LONGITUDE` - The longitude of the location for which you wish to get weather conditions
* `REFRESH_TIME` - Optionally, the number of seconds between refreshing weather data.
    Defaults to 600 seconds, which is the suggested shortest refresh time in the OpenWeather API documentation.

Alternatively, you could create an `env.ini` file in the project's base directory with the following structure:

    [location]
    latitude=XXX.XXXXXX
    longitude=YYY.YYYYYY

    [openweather]
    ow_api_key=0123456789abcdef0123456789abcdef

To run the weather app on a virtual LED display in your venv-activated development environment:

    python examples/weather_app.py

If successful, you should see something like the following, depending on current conditions:

![Weather app screenshot](doc/images/weather_app_screenshot.png)

To run it on the real LED display:

    sudo venv/bin/python examples/weather_app.py

--------
A previous iteration of the weather app used the Visual Crossing API, and the VX API client
module remains in case anyone wants to use it.  There's also a weather.gov client, though
it doesn't furnish current conditions, only forecast predictions.

### OpenWeather API bookmarks

* [List of weather condition codes](https://openweathermap.org/weather-conditions)

### Visual crossings bookmarks
* [Weather data API Documentation](https://www.visualcrossing.com/resources/documentation/weather-api/timeline-weather-api/)
* [ Weather Data Services and URL Builder](https://www.visualcrossing.com/weather/weather-data-services)
* [Weather Condition Translations and ID list](https://docs.google.com/spreadsheets/d/1cc-jQIap7ZToVaEgiXEk_Aa6YVYjSObLV9PMe4oHrFg/edit#gid=1769797687)

# Creating new apps

## Important classes

#### Core classes
Important `lmae.core` classes include:

* `LMAEObject` - the parent of all other library classes
* `Canvas` - onto this actors draw themselves
* `Actor` - an entity that can draw itself and that is positioned on a stage
* `CompositeActor` - an actor that applies a drawing effect to another actor when rendering
* `Animation` - a time based way of updating an actor's position or state
* `Stage` – a complete view that can draw itself to the matrix, containing actors and current animations on them

The core also contains a method used by the app runner to parse command line matrix options (almost all of which
are the same as those used in the
[hzeller library](https://github.com/hzeller/rpi-rgb-led-matrix#changing-parameters-via-command-line-flags)
to configure the LED display driver).

#### Actor classes
Specific actor classes are in `lmae.actor` :

* `StillImage` - A static image, typically loaded from an image file
* `SpriteImage` - A sprite, drawn as a crop of a sprite sheet. A sprite sheet can contain many distinct images
    that can be diplayed one at a time.
* `Text` – An actor that renders text, with a given font. Some free pixel font files are included in the `fonts` folder.
* `EmojiText` – An actor that can render full color emoji glyphs inline with text. This is quite slow, and care must be
    exercised with its use
* `Rectangle` - An actor that draws a rectangle, optionally filled, with options for colors and line thickness.
* `Line` - An actor that draws a line segment from one point to another, with options for color and line thickness.
* `CropMask` - A composite actor that crops another actor into a rectangular viewing area

Note that all these actors render themselves with full alpha channel support.

#### Animation classes
Specific animation classes are in `lmae.animation`:

* `Still` - An animation that does nothing for a defined period of time. Useful to pause in sequences.
* `Easing` - A helper class for specifying a motion easing method. Currently supports linear, quadratic, Bézier,
    parametric, back, and custom easing motions.
* `StraightMove` - Move an actor in a straight line a certain distance over a certain period of time.
* `Sequence` - A composite animation that applies a series of animations, one at a time, to a given actor.

Note that animations are largely composable, meaning that multiple animations can apply to one actor at the same
time and they will all have a cumulative effect.   Animations can optionally be set to repeat once they end,
to enable animation effects of indefinite length.

#### Component classes
Components are actors in `lmae.component` that know how to construct their own animation sequences.

* `Carousel` - Carousels slide several actors through a cropped viewing window, one at a time, with configurable
    pause time and motion time, and then repeats by scrolling back to the first actor
* `AnimatedSprite` - Displays a `SpriteImage` and runs throw
   an animation sequence of frames for the sprite.
* `AnimatedImage`  - Displays a sequence of images. Typically created by loading from an animated GIF. 

## App framework

To support easily writing small apps that use the display to do interesting things,
there is the `lmae.app` module.  In it, there is a class called `App`, which
your app can extend to get access to a basic app running framework.
Your app just needs to know how to `prepare()` itself, how to `run()`, and how to
`stop()`.

To run the app:

    app_runner.start_app(my_app)

This function will run a few helper methods that get your app set up, including
setting up the matrix and matrix options for your app by calling this:

    my_app.set_matrix(app_runner.matrix, options=app_runner.matrix_options)

The app runner waits for a `return` keypress on the console before exiting the app.

The `app_runner` module also includes a helper method to get environmental
properties, set either as `env` variables or in an `env.ini` file: `app_runner.get_env_parameter()`.
Note that the env variable and the env.ini property don't have to have exactly the same name.

### App classes

To save on some of the boilerplate for app development, there are two 
classes in `lmae.app` that your app can choose to extend:

* `SingleStageRenderLoopApp` - A very simple app with one stage and an indefinite
   rendering loop.  Call `my_app.add_actors()` and `my_app.add_animations()` to add
   actors and animations to the stage. Call `my_app.set_pre_render_callback()` to set a function
   that will be called before each rendered frame. This app will run at a frame rate up 
   to the maximum frame rate, which defaults to 120 fps. It works well for the most simple of 
   apps without complex pre-rendering needs.
* `DisplayManagedApp` - A slightly more sophisticated base class. Apps need to 
   set up their own stage, actors, and animations.  Override `my_app.update_view()`
   to make changes that will be displayed on rendering. This method needs to run fast
   to achieve high frame rates, and so calls to data services should be cached.
   The call to `update_view()` includes `elapsed_time` since the app started running.
   The app will only render new frames if the contents of the stage have changed in some
   way to require it.  Each actor tracks its own state to know if a state change requires
   re-rendering. As with the above, it will run at a frame rate up
   to the maximum frame rate, which defaults to 120 fps.
