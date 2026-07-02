import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from troutintel.config import load_river_config
from troutintel.io import load_json, save_json
from troutintel.sources.nws import (
    get_weather_bundle,
    normalize_current_weather,
)


GRID_FIELDS = [
    "skyCover",
    "relativeHumidity",
    "probabilityOfPrecipitation",
    "quantitativePrecipitation",
    "temperature",
    "dewpoint",
    "windSpeed",
    "windGust",
    "windDirection",
]


def safe_load_json(path: str) -> Any:
    try:
        return load_json(path)
    except FileNotFoundError:
        return None


def parse_valid_time_start(valid_time: str) -> Optional[datetime]:
    try:
        start = valid_time.split("/")[0]
        return datetime.fromisoformat(start.replace("Z", "+00:00"))
    except Exception:
        return None


def summarize_numeric(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"min": None, "max": None, "avg": None}

    return {
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "avg": round(sum(values) / len(values), 2),
    }


def build_pressure_trend(
    river_name: str,
    generated_at_utc: str,
    current_pressure_inhg: float | None,
) -> Dict[str, Any]:
    history_path = f"data/weather_history/{river_name}.json"
    history = safe_load_json(history_path) or []

    previous_pressure = None

    if history:
        previous_pressure = history[-1].get("pressure_inhg")

    trend = "unknown"
    change = None

    if current_pressure_inhg is not None and previous_pressure is not None:
        change = round(current_pressure_inhg - previous_pressure, 2)

        if change >= 0.03:
            trend = "rising"
        elif change <= -0.03:
            trend = "falling"
        else:
            trend = "stable"

    history.append(
        {
            "generated_at_utc": generated_at_utc,
            "pressure_inhg": current_pressure_inhg,
        }
    )

    history = history[-24:]

    save_json(history, history_path)

    return {
        "current_inhg": current_pressure_inhg,
        "previous_inhg": previous_pressure,
        "change_since_last_run": change,
        "trend": trend,
    }


def extract_grid_values_48h(
    grid_data: Dict[str, Any],
    field_name: str,
) -> Dict[str, Any]:

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=48)

    field = (
        grid_data
        .get("properties", {})
        .get(field_name)
    )

    if not field:
        return {
            "available": False,
            "unit": None,
            "values": [],
            "summary": None,
        }

    unit = field.get("uom")
    raw_values = field.get("values", [])

    values = []

    for item in raw_values:
        valid_time = item.get("validTime")
        value = item.get("value")

        start_time = parse_valid_time_start(valid_time)

        if start_time is None:
            continue

        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        if not (now <= start_time <= cutoff):
            continue

        values.append(
            {
                "time": start_time.isoformat(),
                "value": value,
            }
        )

    numeric_values = [
        item["value"]
        for item in values
        if isinstance(item["value"], (int, float))
    ]

    return {
        "available": True,
        "unit": unit,
        "values": values,
        "summary": summarize_numeric(numeric_values),
    }


def build_forecast_48h(
    weather_bundle: Dict[str, Any],
) -> Dict[str, Any]:

    grid_data = weather_bundle["grid_data"]

    return {
        field_name: extract_grid_values_48h(
            grid_data,
            field_name,
        )
        for field_name in GRID_FIELDS
    }


async def process_river(
    client: httpx.AsyncClient,
    river_name: str,
    river: dict,
) -> None:

    lat = river["noaa"].get("lat")
    lon = river["noaa"].get("lon")

    if lat is None or lon is None:
        print(f"Skipping {river_name}: no NOAA coordinates")
        return

    generated_at_utc = datetime.now(timezone.utc).isoformat()

    weather_bundle = await get_weather_bundle(
        client=client,
        lat=lat,
        lon=lon,
    )

    current_weather = normalize_current_weather(
        weather_bundle
    )

    forecast_48h = build_forecast_48h(
        weather_bundle
    )

    pressure_trend = build_pressure_trend(
        river_name=river_name,
        generated_at_utc=generated_at_utc,
        current_pressure_inhg=current_weather.get("pressure_inhg"),
    )

    weather_output = {
        "river_key": river_name,
        "river_name": river["display_name"],
        "generated_at_utc": generated_at_utc,
        "current": current_weather,
        "pressure_trend": pressure_trend,
        "forecast_48h": forecast_48h,
    }

    save_json(
        weather_output,
        f"data/weather/{river_name}.json",
    )

    print(f"Wrote {river_name} weather")


async def main():

    rivers = load_river_config()

    async with httpx.AsyncClient(
        headers={
            "User-Agent": (
                "georgiatroutfishing.com, "
                "admin@georgiatroutfishing.com"
            )
        },
        timeout=20.0,
    ) as client:

        tasks = [
            process_river(
                client,
                river_name,
                river,
            )
            for river_name, river in rivers.items()
        ]

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
