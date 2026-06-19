from typing import Any, Dict

import httpx


NWS_BASE_URL = "https://api.weather.gov"

HEADERS = {
    "User-Agent": "georgiatroutfishing.com, admin@georgiatroutfishing.com",
    "Accept": "application/geo+json",
}


async def fetch_json(
    client: httpx.AsyncClient,
    url: str,
) -> Dict[str, Any]:
    response = await client.get(url)
    response.raise_for_status()
    return response.json()


async def get_nws_point_metadata(
    client: httpx.AsyncClient,
    lat: float,
    lon: float,
) -> Dict[str, Any]:
    url = f"{NWS_BASE_URL}/points/{lat},{lon}"
    return await fetch_json(client, url)


async def get_nws_forecast_urls(
    client: httpx.AsyncClient,
    lat: float,
    lon: float,
) -> Dict[str, str]:
    point_data = await get_nws_point_metadata(client, lat, lon)
    properties = point_data["properties"]

    return {
        "daily_forecast_url": properties["forecast"],
        "hourly_forecast_url": properties["forecastHourly"],
        "forecast_grid_data_url": properties["forecastGridData"],
        "observation_stations_url": properties["observationStations"],
    }


async def get_daily_forecast(
    client: httpx.AsyncClient,
    forecast_url: str,
) -> Dict[str, Any]:
    return await fetch_json(client, forecast_url)


async def get_hourly_forecast(
    client: httpx.AsyncClient,
    hourly_forecast_url: str,
) -> Dict[str, Any]:
    return await fetch_json(client, hourly_forecast_url)


async def get_forecast_grid_data(
    client: httpx.AsyncClient,
    grid_data_url: str,
) -> Dict[str, Any]:
    return await fetch_json(client, grid_data_url)


async def get_nearest_observation_station_id(
    client: httpx.AsyncClient,
    observation_stations_url: str,
) -> str:
    stations_data = await fetch_json(client, observation_stations_url)
    first_station = stations_data["features"][0]
    return first_station["properties"]["stationIdentifier"]


async def get_latest_observation(
    client: httpx.AsyncClient,
    station_id: str,
) -> Dict[str, Any]:
    url = f"{NWS_BASE_URL}/stations/{station_id}/observations/latest"
    return await fetch_json(client, url)


def pascals_to_millibars(pressure_pa: float) -> float:
    return pressure_pa / 100


def pascals_to_inches_hg(pressure_pa: float) -> float:
    return pressure_pa / 3386.39


async def get_barometric_pressure(
    client: httpx.AsyncClient,
    observation_stations_url: str,
) -> Dict[str, Any]:
    station_id = await get_nearest_observation_station_id(
        client,
        observation_stations_url,
    )

    observation = await get_latest_observation(client, station_id)

    pressure_pa = (
         observation["properties"]
         .get("barometricPressure", {})
         .get("value")
     )

    if pressure_pa is None:
         return {
             "station_id": station_id,
             "pressure_pa": None,
             "pressure_mb": None,
             "pressure_inhg": None,
             "raw_observation": observation,
         }

    return {
         "station_id": station_id,
         "pressure_pa": pressure_pa,
         "pressure_mb": pascals_to_millibars(pressure_pa),
         "pressure_inhg": pascals_to_inches_hg(pressure_pa),
         "raw_observation": observation,
     }
    
  

async def get_weather_bundle(
    client: httpx.AsyncClient,
    lat: float,
    lon: float,
) -> Dict[str, Any]:
    urls = await get_nws_forecast_urls(
        client=client,
        lat=lat,
        lon=lon,
    )

    daily = await get_daily_forecast(client, urls["daily_forecast_url"])
    hourly = await get_hourly_forecast(client, urls["hourly_forecast_url"])
    grid = await get_forecast_grid_data(client, urls["forecast_grid_data_url"])
    pressure = await get_barometric_pressure(
        client,
        urls["observation_stations_url"],
    )

    return {
        "lat": lat,
        "lon": lon,
        "urls": urls,
        "daily_forecast": daily,
        "hourly_forecast": hourly,
        "grid_data": grid,
        "barometric_pressure": pressure,
    }


def normalize_current_weather(
    weather_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    first_hour = weather_bundle["hourly_forecast"]["properties"]["periods"][0]
    pressure = weather_bundle["barometric_pressure"]

    return {
        "latitude": weather_bundle["lat"],
        "longitude": weather_bundle["lon"],
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
