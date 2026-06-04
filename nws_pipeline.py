import asyncio
from typing import Any, Dict

import httpx

NWS_BASE_URL = "https://api.weather.gov"

"""
buford dam coordinates
"""
BUFORD_DAM_LAT = 34.1567
BUFORD_DAM_LON = -84.0784

HEADERS = {
    "User-Agent": "georgiaflyfishingguides.com, admin@georgiaflyfishingguides.com",
    "Accept": "application/geo+json",
}


async def fetch_json(client: httpx.AsyncClient, url:str) -> Dict[str, Any]:

	"""
    helper function that calls apis and retrieves json content

	Make one HTTP GET request and deserialize the JSON response
	into a Python dictionary.

	'await' means:
	while this request waits on the network, let other async tasks run.
	"""

	response = await client.get(url)
	response.raise_for_status()
	return response.json()


async def get_nws_point_metadata(
	client: httpx.AsyncClient,
	lat: float,
	lon: float,
	) -> Dict[str, Any]:
	
	"""
    function just collects relevant urls for our lat and long points
	
    Ask NWS what forecast grid/office handles this lattitude and longitude.

	This does NOT return the forecast itself.
	It returns metadata, including URLs for:
	- daily forecast
	- hourly forecast
	- observation stations

	"""

	url = f"{NWS_BASE_URL}/points/{lat},{lon}"
	return await fetch_json(client, url)

async def get_nws_forecast_urls(
	client: httpx.AsyncClient,
	lat: float,
	lon: float, 
	) -> Dict[str, str]:

	"""
	Extract the useful forecast URLs from the NWS point metadata.

    get_nws_point_metadata returns a json response that contains urls for forecasts for the specific lat and long points
	"""

	point_data = await get_nws_point_metadata(client, lat, lon)
	
	properties = point_data["properties"]

	return {
		"daily_forecast_url": properties["forecast"],
		"hourly_forecast_url": properties["forecastHourly"],
		"forecast_grid_data_url": properties["forecastGridData"],
		"observation_station_url": properties["observationStations"],
	}


async def get_daily_forecast(
    client: httpx.AsyncClient,
    forecast_url: str,
) -> Dict[str, Any]:
    """
    Fetch the normal NWS daily/period forecast.
    Example: Today, Tonight, Friday, Friday Night, etc.
    """
    return await fetch_json(client, forecast_url)


async def get_hourly_forecast(
    client: httpx.AsyncClient,
    hourly_forecast_url: str,
) -> Dict[str, Any]:
    """
    Fetch the hourly NWS forecast.
    This is probably more useful for fishing:
    - temperature trend
    - wind trend
    - precipitation chance
    - cloud cover clues from shortForecast
    """
    return await fetch_json(client, hourly_forecast_url)


async def get_forecast_grid_data(
    client: httpx.AsyncClient,
    grid_data_url: str,
) -> Dict[str, Any]:
    """
    Fetch more detailed gridded forecast data.

    This can include fields like:
    - temperature
    - dewpoint
    - wind speed
    - sky cover
    - probability of precipitation
    - quantitative precipitation forecast

    This is more detailed but also more complex.
    """
    return await fetch_json(client, grid_data_url)

async def get_nearest_observation_station_id(
    client: httpx.AsyncClient,
    observation_stations_url: str,
) -> str:

    """
    this will get the station id for what i think is the nearest station
    when you feed the base url with the proper lat and lon to the api
    it'll list stations in order of nearest to your target area

    so, we grab the station id of the first station
    """
    stations_data = await fetch_json(client, observation_stations_url)
    first_station = stations_data["features"][0]
    return first_station["properties"]["stationIdentifier"]

async def get_latest_observation(
    client: httpx.AsyncClient,
    station_id: str,
) -> Dict[str, Any]:
    url = f"{NWS_BASE_URL}/stations/{station_id}/observations/latest"
    return await fetch_json(client, url)


def pascals_to_millibars(pressure_pa: float)-> float:
    return pressure_pa/100

def pascals_to_inches_hg(pressure_pa: float) -> float:
    return pressure_pa / 3386.39

async def get_barometric_pressure(
    client: httpx.AsyncClient,
    observation_stations_url: str,
) -> Dict[str, Any]:
    station_id = await get_nearest_observation_station_id(
        client,
        observation_stations_url,)

    observation = await get_latest_observation(client, station_id)

    pressure_pa = observation["properties"]["barometricPressure"]["value"]

    return{
        "station_id": station_id,
        "pressure_pa": pressure_pa,
        "pressure_mb": pascals_to_millibars(pressure_pa),
        "pressure_inhg": pascals_to_inches_hg(pressure_pa),
        "raw_observation": observation,
    }


async def get_buford_dam_weather_bundle() -> Dict[str, Any]:
    """
    Main orchestration function.

    This gets all NWS weather data we currently care about
    for Buford Dam / Chattahoochee below the dam.
    """
    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=20.0,
    ) as client:

        urls = await get_nws_forecast_urls(
            client=client,
            lat=BUFORD_DAM_LAT,
            lon=BUFORD_DAM_LON,
        )

        daily_task = get_daily_forecast(client, urls["daily_forecast_url"])
        hourly_task = get_hourly_forecast(client, urls["hourly_forecast_url"])
        grid_task = get_forecast_grid_data(client, urls["forecast_grid_data_url"])
        pressure_task = get_barometric_pressure(
            client,
            urls["observation_station_url"]
            )

        daily, hourly, grid, pressure = await asyncio.gather(
            daily_task,
            hourly_task,
            grid_task,
            pressure_task
        )

        return {
            "location": {
                "name": "Chattahoochee River below Buford Dam",
                "lat": BUFORD_DAM_LAT,
                "lon": BUFORD_DAM_LON,
            },
            "urls": urls,
            "daily_forecast": daily,
            "hourly_forecast": hourly,
            "grid_data": grid,
            "barometric_pressure": pressure,
        }

def normalize_current_weather(weather_bundle: Dict[str, Any]) -> Dict[str, Any]:
    first_hour = weather_bundle["hourly_forecast"]["properties"]["periods"][0]
    pressure = weather_bundle["barometric_pressure"]

    return {
        "location_name": weather_bundle["location"]["name"],
        "latitude": weather_bundle["location"]["lat"],
        "longitude": weather_bundle["location"]["lon"],

        "forecast_time": first_hour["startTime"],
        "air_temp_f": first_hour["temperature"],
        "temperature_unit": first_hour["temperatureUnit"],
        "wind_speed": first_hour["windSpeed"],
        "wind_direction": first_hour["windDirection"],
        "short_forecast": first_hour["shortForecast"],

        "pressure_station": pressure["station_id"],
        "pressure_mb": round(pressure["pressure_mb"], 1),
        "pressure_inhg": round(pressure["pressure_inhg"], 2),
    }

if __name__ == "__main__":
    weather_bundle = asyncio.run(get_buford_dam_weather_bundle())

    print(weather_bundle["location"])
    print(weather_bundle["urls"])

    pressure = weather_bundle["barometric_pressure"]

    print("Station:", pressure["station_id"])
    print("Pressure mb:", pressure["pressure_mb"])
    print("Pressure inHg:", pressure["pressure_inhg"])

    first_hour = weather_bundle["hourly_forecast"]["properties"]["periods"][0]


if __name__ == "__main__":
    weather_bundle = asyncio.run(get_buford_dam_weather_bundle())

    current_weather = normalize_current_weather(weather_bundle)

    print(current_weather)