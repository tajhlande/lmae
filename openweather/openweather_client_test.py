import configparser
import logging
import json
import os
from openweather_client import get_conditions_and_forecast_by_lat_long

config = configparser.ConfigParser()
config.read('env.ini')

api_key = os.environ.get('OW_API_KEY')

if not api_key:
    api_key = config['openweather']['ow_api_key']

logging.info(f"Got api key: {'true' if api_key else 'false'}")

latitude = os.environ.get('LATITUDE')
if not latitude:
    latitude = config['location']['latitude']

longitude = os.environ.get('LONGITUDE')
if not longitude:
    longitude = config['location']['longitude']

wj = get_conditions_and_forecast_by_lat_long(latitude=latitude, longitude=longitude, api_key=api_key)

print(json.dumps(wj, sort_keys=True, indent=4))
