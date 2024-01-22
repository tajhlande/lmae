import asyncio
import datetime
import time

from datetime import datetime, timezone
from math import sin, cos, asin, atan2, radians, degrees, pi, sqrt, isclose, floor
from PIL import Image, ImageDraw, ImageFont

import app_runner
from lmae.core import Stage
from lmae.app import App
from lmae.actor import StillImage

# logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)12s [%(levelname)5s]: %(message)s')
# logger = logging.getLogger("world_clock")
# logger.setLevel(logging.DEBUG)


def normalize_radians(rads):
    while rads > pi:
        rads = rads - pi
    while rads < -pi:
        rads = rads + pi
    return rads


def normalize_longitude(degs):
    """
    Ensure that a calculated longitude `l` that is outside `-180 <= l <= 180`
    is normalized to be within that range
    :param degs: the latitude in degrees
    :return: the normalized latitude in degrees
    """
    while degs > 180:
        degs = degs - 360
    while degs < -180:
        degs = degs + 360
    return degs


def compute_sun_declination(day_of_year):
    """
    From https://www.aa.quae.nl/en/antwoorden/zonpositie.html#v526
    Compute the declination of the sun on a given day.

    :param day_of_year: number of days since (the beginning of) the most recent December 31st (i.e., for midnight
                        at the beginning of January 1st, for January 2nd, and so on).
    :return: The declination of the sun on that day, in degrees.
             The declination is the coordinate in the equatorial coordinate system in the sky that is similar to
             latitude on Earth. It ranges between −90 degrees at the southern celestial pole and +90 degrees at
             the northern celestial pole and is zero at the celestial equator. The other equatorial coordinate is
             the right ascension.
    """
    M = -3.6 + 0.9856 * day_of_year
    nu = M + 1.9 * sin(radians(M))
    rad_lambda = radians(nu + 102.9)
    sin_lambda = sin(rad_lambda)
    delta = -22.8 * sin_lambda + 0.6 * pow(sin_lambda, 3)
    return delta


def compute_terminator_for_declination_and_angle(declination, hour_of_day, angle):
    """
    Given a declination angle of the sun and an angle around the terminator, compute the
    corresponding latitude and longitude.

    :param declination: Declination of the sun on the given day, in degrees
    :param hour_of_day: UTC hours of the day
    :param angle: An angle around the circle of the terminator, in degrees
    :return: A pair (L, B) that is a north latitude and east longitude on the terminator, in degrees
    """
    b = declination
    l = normalize_longitude(180 - 15 * hour_of_day)
    # psi = angle
    rad_b = radians(b)
    rad_l = radians(l)
    rad_psi = radians(angle)
    B = asin(cos(rad_b) * sin(rad_psi))
    x = -cos(rad_l) * sin(rad_b) * sin(rad_psi) - sin(rad_l) * cos(rad_psi)
    y = -sin(rad_l) * sin(rad_b) * sin(rad_psi) + cos(rad_l) * cos(rad_psi)
    L = atan2(y, x)

    return degrees(B), degrees(L)


_gall_peters_radius = 34.4 / pi
_root_2 = sqrt(2)
_root_2_x_180 = _root_2 * 180


def half_round_up(value: float) -> float:
    return floor(value + 0.5)


def gall_peters_projection(lat_long: tuple[float, float]) -> tuple[int, int]:
    # Gall-Peters projection onto X, Y screen coords.
    # north and east are positive lat and long
    # X, Y (0, 0) is upper left corner of screen
    # aspect ratio adjusted to 2:1 (from default pi / 2:1)
    # a few tweaks via multiplication parameters to get the projection to exactly match the screen in integers
    x = int(half_round_up((_gall_peters_radius * lat_long[1]) * 4 / _root_2_x_180) * 1.03 + 32)
    y = int(-(half_round_up(_gall_peters_radius * _root_2 * sin(radians(lat_long[0])))) * 1.05 + 16)
    return x, y


def is_equinox(declination):
    """
    Given a solar declination, decide if it is the equinox
    :param declination: solar declination in degrees
    :return: True if equinox, False otherwise
    """
    return isclose(declination, 0.0, abs_tol=0.20)


_WHITE = 255  # (255, 255, 255, 255)
_BLACK = 0  # (0, 0, 0, 255)


def draw_day_night_mask(declination: float, hour_of_day: float) -> Image:
    """
    Given a declination and an hour of the day, compute and draw day and night
    as white and black for an image with 64 longitudes, and 32 latitudes,
    in Gall-Peters projection.

    :param declination: angle to the sun, in degrees
    :param hour_of_day: hour of the day, in UTC
    :return: A list of tuples, where the index in the list is the x coordinate,
             the first int is the y coordinate, and the second int is latitudinally pointing to daylight
            (+1 for northern sunlight or -1 for southern sunlight)
    """
    image = Image.new("L", (64, 32), _BLACK)
    image_draw = ImageDraw.Draw(image)
    # logger.debug(f"Declination: {declination:0.3f}, hour: {hour_of_day}")

    # check for equinoxes
    if is_equinox(declination):
        # compute the terminator just at the east and west extremes
        # logger.debug(f"It's an equinox!")
        right_terminator = compute_terminator_for_declination_and_angle(declination, hour_of_day, 0)
        left_terminator = compute_terminator_for_declination_and_angle(declination, hour_of_day, 180)
        left_term_xy = gall_peters_projection(left_terminator)
        right_term_xy = gall_peters_projection(right_terminator)
        # logger.debug(f"Left and right terminators: {left_terminator}, {right_terminator} and xy: "
        #              f"{left_term_xy}, {right_term_xy} at hour {hour_of_day}")
        if right_term_xy[0] > left_term_xy[0]:
            # sun zone is contained entirely within the map
            xy = ((left_term_xy[0], 0), (right_term_xy[0], 31))
            # logger.debug(f"Drawing rect at {xy}")
            image_draw.rectangle(xy, fill=_WHITE)
        else:
            # sun zone is split on left and right edges of the map
            xy = ((0, 0), (right_term_xy[0], 31))
            # logger.debug(f"Drawing rect 1 at {xy}")
            image_draw.rectangle(xy, fill=_WHITE)
            xy = ((left_term_xy[0], 0), (63, 31))
            # logger.debug(f"Drawing rect 2 at {xy}")
            image_draw.rectangle(xy, fill=_WHITE)

    else:
        # not an equinox, so let's draw the sun curve
        term_angle = 0
        first_term_pt = None
        last_term_pt = None
        last_term_pt_xy = None
        while term_angle < 360:
            terminator_pt = compute_terminator_for_declination_and_angle(declination, hour_of_day, term_angle)
            term_pt_xy = gall_peters_projection(terminator_pt)
            # logger.debug(f"Terminator at {term_angle}º: {terminator_pt}, xy: {term_pt_xy}")
            if not first_term_pt:
                first_term_pt = terminator_pt
            if last_term_pt:
                # compute map boundary points
                if declination > 0:
                    # sun is in northern hemisphere
                    outer_boundary_pt_1 = last_term_pt_xy[0], 0
                    outer_boundary_pt_2 = term_pt_xy[0], 0
                else:
                    # sun is in southern hemisphere
                    outer_boundary_pt_1 = last_term_pt_xy[0], 31
                    outer_boundary_pt_2 = term_pt_xy[0], 31

                # draw a quadrilateral
                if abs(terminator_pt[1] - last_term_pt[1]) > 90:
                    # we probably wrapped around, so draw two separate quads
                    if outer_boundary_pt_1[0] < 32:
                        ob1x = 0
                        ob2x = 63
                    else:
                        ob1x = 63
                        ob2x = 0
                    xy = [outer_boundary_pt_1, (ob1x, outer_boundary_pt_2[1]), (ob1x, term_pt_xy[1]), last_term_pt_xy]
                    # logger.debug(f"Polygon 1 xy: {xy}")
                    image_draw.polygon(xy, fill=_WHITE)
                    xy = [outer_boundary_pt_2, (ob2x, outer_boundary_pt_1[1]), (ob2x, last_term_pt_xy[1]), term_pt_xy]
                    # logger.debug(f"Polygon 2 xy: {xy}")
                    image_draw.polygon(xy, fill=_WHITE)
                else:
                    # draw one quadrilateral
                    xy = [outer_boundary_pt_1, outer_boundary_pt_2, term_pt_xy, last_term_pt_xy]
                    # logger.debug(f"Polygon xy: {xy}")
                    image_draw.polygon(xy, fill=_WHITE)
            last_term_pt = terminator_pt
            last_term_pt_xy = term_pt_xy
            term_angle = term_angle + 5   # a guess at what accuracy is good enough for a 64 bit screen

    return image


class WorldClock(App):
    """
    Display a projection of the world with a day-night separator.
    """

    # noinspection PyTypeChecker
    def __init__(self, refresh_time: int = 300):
        super().__init__()
        self.stage: Stage = None
        self.actors = list()
        self.pre_render_callback = None
        self.refresh_time = refresh_time
        self.big_font = ImageFont.truetype("fonts/Roboto/Roboto-Light.ttf", 15)
        self.daytime_map_image = Image.open("images/visible-earth/world-topo-bathy.png")
        self.nighttime_map_image = Image.open("images/visible-earth/black-marble.png")
        self.composite_map = StillImage(name="composite-map")
        self.current_datetime_utc: datetime = None
        self.last_view_update_datetime_utc: datetime = None

    def compose_view(self):
        self.stage = Stage(matrix=self.matrix, matrix_options=self.matrix_options)
        self.stage.actors.append(self.composite_map)

    def time_to_update(self):
        self.current_datetime_utc = datetime.now(timezone.utc)
        return (not self.last_view_update_datetime_utc or
                (self.current_datetime_utc - self.last_view_update_datetime_utc).total_seconds() > (60 * 60))

    def update_view(self):
        # see if we need to update the map
        if self.time_to_update():
            self.logger.debug(f"Updating view")

            current_timetuple = self.current_datetime_utc.timetuple()
            day_of_year = current_timetuple[7]
            self.logger.info(f"Day of year: {day_of_year}")

            declination = compute_sun_declination(day_of_year)
            self.logger.info(f"Declination of sun: {declination:.3f}")

            hour_of_day = current_timetuple[3]
            self.logger.info(f"UTC hour of day: {hour_of_day}")

            day_night_mask_image = draw_day_night_mask(declination, hour_of_day)
            # composite_image = Image.new("RGBA", (64, 32), _BLACK)
            composite_image = Image.composite(self.daytime_map_image, self.nighttime_map_image, day_night_mask_image)
            self.composite_map.set_from_image(composite_image)

            self.last_view_update_datetime_utc = self.current_datetime_utc

    def prepare(self):
        self.compose_view()

    async def run(self):
        await super().run()
        self.logger.debug("Run started")
        # self.compose_view()
        max_frame_rate = 20
        min_time_per_frame = 1.0 / max_frame_rate

        try:
            while self.running:
                # update the view
                self.update_view()
                if self.stage.needs_render:
                    self.stage.render_frame()

                # wait 5 minutes
                waiting = True
                wait_start = time.time()
                self.logger.debug(f"Waiting {self.refresh_time / 60} minutes to refresh view")
                last_time = time.perf_counter()
                while waiting and self.running:
                    current_time = time.time()
                    elapsed_time = current_time - wait_start
                    self.update_view()
                    # self.stage.needs_render = True  # have to force this for some reason
                    self.stage.render_frame()
                    waiting = elapsed_time < self.refresh_time

                    # calculate the frame rate and render that
                    render_end_time = time.perf_counter()

                    # if we are rendering faster than max frame rate, slow down
                    elapsed_render_time = render_end_time - last_time
                    if elapsed_render_time < min_time_per_frame:
                        sleep_time = min_time_per_frame - elapsed_render_time
                        # self.logger.debug(f"Sleeping for {sleep_time}")
                        await asyncio.sleep(sleep_time)
                    else:
                        # gotta yield control, with minimal sleep amount
                        await asyncio.sleep(min_time_per_frame/10.0)

                    # mark the timestamp
                    last_time = time.perf_counter()

        finally:
            self.logger.debug("Run stopped")


if __name__ == "__main__":
    # get environment variables
    app_runner.app_setup()
    world_clock = WorldClock()
    world_clock.set_matrix(app_runner.matrix, options=app_runner.matrix_options)
    app_runner.start_app(world_clock)
