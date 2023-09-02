import requests
from munch import Munch

"""
Open Weather API Client

Geocoding API converts places (ZIP) to lat long
http://api.openweathermap.org/geo/1.0/zip?zip={zip code},{country code}&appid={API key}

Example response:
{
  "zip": "90210",
  "name": "Beverly Hills",
  "lat": 34.0901,
  "lon": -118.4065,
  "country": "US"
}

Our lat long: 39.0158678,-77.0734945

OneCall API 
https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&units={units}&exclude={part}&appid={API key}
units can be standard, metric, or imperial

API Docs on data in response https://openweathermap.org/api/one-call-3#parameter

Example response:
{
   "lat":33.44,
   "lon":-94.04,
   "timezone":"America/Chicago",
   "timezone_offset":-18000,
   "current":{
      "dt":1684929490,
      "sunrise":1684926645,
      "sunset":1684977332,
      "temp":292.55,
      "feels_like":292.87,
      "pressure":1014,
      "humidity":89,
      "dew_point":290.69,
      "uvi":0.16,
      "clouds":53,
      "visibility":10000,
      "wind_speed":3.13,
      "wind_deg":93,
      "wind_gust":6.71,
      "weather":[
         {
            "id":803,
            "main":"Clouds",
            "description":"broken clouds",
            "icon":"04d"
         }
      ]
   },
   "minutely":[
      {
         "dt":1684929540,
         "precipitation":0
      },
      ...
   ],
   "hourly":[
      {
         "dt":1684926000,
         "temp":292.01,
         "feels_like":292.33,
         "pressure":1014,
         "humidity":91,
         "dew_point":290.51,
         "uvi":0,
         "clouds":54,
         "visibility":10000,
         "wind_speed":2.58,
         "wind_deg":86,
         "wind_gust":5.88,
         "weather":[
            {
               "id":803,
               "main":"Clouds",
               "description":"broken clouds",
               "icon":"04n"
            }
         ],
         "pop":0.15
      },
      ...
   ],
   "daily":[
      {
         "dt":1684951200,
         "sunrise":1684926645,
         "sunset":1684977332,
         "moonrise":1684941060,
         "moonset":1684905480,
         "moon_phase":0.16,
         "summary":"Expect a day of partly cloudy with rain",
         "temp":{
            "day":299.03,
            "min":290.69,
            "max":300.35,
            "night":291.45,
            "eve":297.51,
            "morn":292.55
         },
         "feels_like":{
            "day":299.21,
            "night":291.37,
            "eve":297.86,
            "morn":292.87
         },
         "pressure":1016,
         "humidity":59,
         "dew_point":290.48,
         "wind_speed":3.98,
         "wind_deg":76,
         "wind_gust":8.92,
         "weather":[
            {
               "id":500,
               "main":"Rain",
               "description":"light rain",
               "icon":"10d"
            }
         ],
         "clouds":92,
         "pop":0.47,
         "rain":0.15,
         "uvi":9.23
      },
      ...
   ],
    "alerts": [
    {
      "sender_name": "NWS Philadelphia - Mount Holly (New Jersey, Delaware, Southeastern Pennsylvania)",
      "event": "Small Craft Advisory",
      "start": 1684952747,
      "end": 1684988747,
      "description": "...SMALL CRAFT ADVISORY REMAINS IN EFFECT FROM 5 PM THIS\n
                      AFTERNOON TO 3 AM EST FRIDAY...\n
                      * WHAT...North winds 15 to 20 kt with gusts up to 25 kt and seas\n
                      3 to 5 ft expected.\n
                      * WHERE...Coastal waters from Little Egg Inlet to Great Egg\n
                      Inlet NJ out 20 nm, Coastal waters from Great Egg Inlet to\n
                      Cape May NJ out 20 nm and Coastal waters from Manasquan Inlet\n
                      to Little Egg Inlet NJ out 20 nm.\n
                      * WHEN...From 5 PM this afternoon to 3 AM EST Friday.\n
                      * IMPACTS...Conditions will be hazardous to small craft.",
      "tags": [

      ]
    },
    ...
  ]

"""


def get_conditions_and_forecast_by_lat_long(latitude: str, longitude: str, api_key: str):
    units = 'imperial'
    part = 'alerts'
    endpoint = f'https://api.openweathermap.org/data/3.0/onecall?lat={latitude}&lon={longitude}&units={units}' \
               f'&exclude={part}&appid={api_key}'

    headers = {'User-Agent': 'com.bluefilament.rpi-matrix.weather'}
    with requests.get(endpoint, headers=headers) as request:
        if request.status_code == requests.codes.ok:
            return Munch.fromDict(request.json())
        else:
            request.raise_for_status()
