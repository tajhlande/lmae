import requests
from munch import Munch


def get_forecast_by_gridpoint(station: str, gridpoint: str):
    endpoint = f'https://api.weather.gov/gridpoints/{station}/{gridpoint}/forecast'
    headers = {'User-Agent': '(com.bluefilament.rpi-matrix.weather, tajhlande@gmail.com)',
               'Accept': 'application/geo+json'}
    with requests.get(endpoint, headers=headers) as request:
        if request.status_code == requests.codes.ok:
            return Munch.fromDict(request.json())
        else:
            request.raise_for_status()






