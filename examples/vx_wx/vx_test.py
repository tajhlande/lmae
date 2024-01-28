import configparser
import logging
import json
import os
from vx_client import get_conditions_and_forecast_by_zipcode


api_key = os.environ.get('VX_API_KEY')

if not api_key:
    config = configparser.ConfigParser()
    config.read('env.ini')
    api_key = config['visual.crossing']['vx_api_key']

logging.info(f"Got api key: {'true' if api_key else 'false'}")

wj = get_conditions_and_forecast_by_zipcode('20895', api_key)

print(json.dumps(wj, sort_keys=True, indent=4))
