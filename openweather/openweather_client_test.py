import configparser
import logging
import json
import os
from openweather_client import get_conditions_and_forecast_by_lat_long


api_key = os.environ.get('OW_API_KEY')

if not api_key:
    config = configparser.ConfigParser()
    config.read('env.ini')
    api_key = config['openweather']['ow_api_key']

logging.info(f"Got api key: {'true' if api_key else 'false'}")

wj = get_conditions_and_forecast_by_lat_long('39.0158678', '-77.0734945', api_key)

print(json.dumps(wj, sort_keys=True, indent=4))
