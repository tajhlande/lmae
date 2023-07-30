
import requests
from munch import Munch


def get_current_conditions_by_zipcode(zipcode: str, api_key: str):
    endpoint = f'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{zipcode}?' \
               f'unitGroup=us&include=current&key={api_key}&contentType=json'

    filtered_endpoint = f'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/' \
                        f'{zipcode}?unitGroup=us&elements=datetime%2CdatetimeEpoch%2Clatitude%2Clongitude%2C' \
                        f'tempmax%2Ctempmin%2Ctemp%2Cfeelslikemax%2Cfeelslikemin%2Cfeelslike%2Cdew%2Cprecip%2C' \
                        f'precipprob%2Cprecipcover%2Csnow%2Cwindgust%2Cwindspeed%2Ccloudcover%2Csunrise%2Csunset%2C' \
                        f'moonphase%2Cconditions%2Cdescription%2Csource&include=current&' \
                        f'key={api_key}&contentType=json'

    headers = {'User-Agent': '(com.bluefilament.rpi-matrix.weather, tajhlande@gmail.com)'}
    with requests.get(filtered_endpoint, headers=headers) as request:
        if request.status_code == requests.codes.ok:
            return Munch.fromDict(request.json())
        else:
            request.raise_for_status()

