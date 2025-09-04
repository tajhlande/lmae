import os
import time
import unittest

from examples.weather_app import WeatherApp
import examples.weather_app
from tests.testing_matrix import TestingRGBMatrix, TestingRGBMatrixOptions
from lmae import app_runner

class WeatherAppTest(unittest.TestCase):
    def test_updated_text_scrolling(self):
        matrix_options = TestingRGBMatrixOptions()
        matrix_options.rows = 32
        matrix_options.cols = 64    
        app_runner.matrix_options = matrix_options
        matrix = TestingRGBMatrix(matrix_options)

        app = WeatherApp(api_key="XXX", latitude = "0.0", longitude = "0.0", 
                         resource_path = os.path.dirname(examples.weather_app.__file__))
        app.set_matrix(matrix=matrix, options=matrix_options)
        app.prepare()

        # set weather conditions to sunny
        app.last_weather_data_at = time.time()
        app.call_status = "ok"
        app.fresh_weather_data = True
        # OpenWeather API response format
        app.temperature_str = f"92º"
        app.feels_like_str = f"FL 96º"
        app.dewpoint_str = f"Dew 72º"
        app.humidity_str = f"RH 66%"
        app.low_temp_str = f"Low 68º"
        app.high_temp_str = f"Hi 101º"
        app.sunrise = 1756982409
        app.sunset = 1757028885
        app.condition_code = 800
        app.condition_short_desc = "sunny"
        app.condition_long_desc = "sunny"
        app.is_daytime = True
        app.condition_short_desc_list = ["sunny"]
        app.condition_long_desc_list = ["sunny"]
        app.combined_short_desc = ', '.join(app.condition_short_desc_list)
        app.combined_long_desc = ', '.join(app.condition_long_desc_list)
        app.need_to_update_condition_desc_animation = True

        app.moon_phase_num = 0.25
        app.moonrise = 1757028885
        app.moonset = 1756982409
        app.is_moon_out = None

        app.update_view(0)

        self.assertTrue(len(app.stage.get_animations_for(app.condition_description_label)) == 0)

        # now add a longer description
        app.condition_short_desc = "scattered clouds"
        app.condition_long_desc = "scattered clouds"
        app.condition_short_desc_list = ["scattered clouds"]
        app.condition_long_desc_list = ["scattered clouds"]
        app.combined_short_desc = ', '.join(app.condition_short_desc_list)
        app.combined_long_desc = ', '.join(app.condition_long_desc_list)
        app.need_to_update_condition_desc_animation = True
        app.prepare()
        app.update_view(1)

        self.assertTrue(len(app.stage.get_animations_for(app.condition_description_label)) > 0)

        # now back to a short description
        app.condition_short_desc = "sunny"
        app.condition_long_desc = "sunny"
        app.condition_short_desc_list = ["sunny"]
        app.condition_long_desc_list = ["sunny"]
        app.combined_short_desc = ', '.join(app.condition_short_desc_list)
        app.combined_long_desc = ', '.join(app.condition_long_desc_list)
        app.need_to_update_condition_desc_animation = True
        app.prepare()
        app.update_view(2)

        self.assertTrue(len(app.stage.get_animations_for(app.condition_description_label)) == 0)

        # now back to a really long description
        app.condition_short_desc = "scattered clouds with a chance of meatballs"
        app.condition_long_desc = "scattered clouds with a chance of meatballs"
        app.condition_short_desc_list = ["scattered clouds with a chance of meatballs"]
        app.condition_long_desc_list = ["scattered clouds with a chance of meatballs"]
        app.combined_short_desc = ', '.join(app.condition_short_desc_list)
        app.combined_long_desc = ', '.join(app.condition_long_desc_list)
        app.need_to_update_condition_desc_animation = True
        app.prepare()
        app.update_view(3)

        self.assertTrue(len(app.stage.get_animations_for(app.condition_description_label)) >= 0)




if __name__ == '__main__':
    unittest.main()