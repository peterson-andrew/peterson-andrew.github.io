from datetime import datetime
from typing import Any, Dict, List, Optional

from troutintel.config import load_river_config
from troutintel.io import load_json, save_json


RIVERS = [
    "chattahoochee",
    "toccoa",
    "soque",
    "etowah",
    "nantahala",
]

def build_usgs_summary(usgs: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not usgs:
        return None

    readings = usgs.get("readings", {})

    water_temp = readings.get("water_temp")
    flow = readings.get("flow_cfs")
    gage = readings.get("gage_height_ft")
    turbidity = readings.get("turbidity")

    observed_at = None
    for reading in (water_temp, flow, gage, turbidity):
        if reading and reading.get("timestamp"):
            observed_at = reading["timestamp"]
            break

    return {
        "site_name": usgs.get("site_name"),
        "water_temp_f": water_temp.get("value_f") if water_temp else None,
        "flow_cfs": flow.get("value") if flow else None,
        "gage_height_ft": gage.get("value") if gage else None,
        "turbidity": turbidity.get("value") if turbidity else None,
        "observed_at": observed_at,
    }

def safe_load_json(path: str) -> Any:
    try:
        return load_json(path)
    except FileNotFoundError:
        return None


def c_to_f(c: Optional[float]) -> Optional[float]:
    if c is None:
        return None
    return round((c * 9 / 5) + 32, 1)


def kmh_to_mph(kmh: Optional[float]) -> Optional[float]:
    if kmh is None:
        return None
    return round(kmh * 0.621371, 1)


def mm_to_inches(mm: Optional[float]) -> Optional[float]:
    if mm is None:
        return None
    return round(mm / 25.4, 2)


def summarize_values(values: List[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {
            "min": None,
            "max": None,
            "avg": None,
        }

    return {
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "avg": round(sum(values) / len(values), 2),
    }


def get_grid_values(
    weather: Dict[str, Any],
    field_name: str,
) -> List[Dict[str, Any]]:
    return (
        weather
        .get("forecast_48h", {})
        .get(field_name, {})
        .get("values", [])
    )


def parse_time(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except Exception:
        return None


def split_forecast_windows(
    weather: Dict[str, Any],
) -> Dict[str, Dict[str, Dict[str, Any]]]:

    all_times = []

    for item in get_grid_values(weather, "temperature"):
        parsed = parse_time(item["time"])

        if parsed is not None:
            all_times.append(parsed)

    if not all_times:
        return {}

    start_date = min(all_times).date()

    windows = {
        "day1": {
            "date": str(start_date),
            "morning": {},
            "afternoon": {},
            "evening": {},
        },
        "day2": {
            "date": str(start_date),
            "morning": {},
            "afternoon": {},
            "evening": {},
        },
    }

    def window_for_time(dt: datetime) -> Optional[str]:
        hour = dt.hour

        if 5 <= hour < 12:
            return "morning"

        if 12 <= hour < 18:
            return "afternoon"

        if 18 <= hour < 24:
            return "evening"

        return None

    def day_key_for_time(dt: datetime) -> Optional[str]:
        delta_days = (dt.date() - start_date).days

        if delta_days == 0:
            return "day1"

        if delta_days == 1:
            return "day2"

        return None

    fields = {
        "sky_cover": "skyCover",
        "humidity": "relativeHumidity",
        "rain_probability": "probabilityOfPrecipitation",
        "rain_inches": "quantitativePrecipitation",
        "air_temp_f": "temperature",
        "wind_mph": "windSpeed",
        "wind_gust_mph": "windGust",
    }

    buckets: Dict[str, Dict[str, Dict[str, List[float]]]] = {}

    for output_name, field_name in fields.items():
        for item in get_grid_values(weather, field_name):
            dt = parse_time(item["time"])
            value = item.get("value")

            if dt is None or value is None:
                continue

            day_key = day_key_for_time(dt)
            window_key = window_for_time(dt)

            if day_key is None or window_key is None:
                continue

            converted_value = value

            if output_name == "air_temp_f":
                converted_value = c_to_f(value)

            if output_name in ["wind_mph", "wind_gust_mph"]:
                converted_value = kmh_to_mph(value)

            if output_name == "rain_inches":
                converted_value = mm_to_inches(value)

            buckets.setdefault(day_key, {})
            buckets[day_key].setdefault(window_key, {})
            buckets[day_key][window_key].setdefault(output_name, [])
            buckets[day_key][window_key][output_name].append(
                converted_value
            )

    for day_key, day_windows in buckets.items():
        for window_key, values_by_field in day_windows.items():
            for field_name, values in values_by_field.items():
                windows[day_key][window_key][field_name] = summarize_values(
                    values
                )

    return windows


def summarize_weather(weather: Dict[str, Any]) -> Dict[str, Any]:
    if weather is None:
        return {}

    current = weather["current"]
    forecast = weather["forecast_48h"]

    temp_summary = forecast["temperature"]["summary"]
    wind_summary = forecast["windSpeed"]["summary"]
    gust_summary = forecast["windGust"]["summary"]
    rain_summary = forecast["quantitativePrecipitation"]["summary"]

    return {
        "pressure_inhg": current["pressure_inhg"],
        "air_temp": {
            "current_f": current["air_temp_f"],
            "low_f": c_to_f(temp_summary["min"]),
            "high_f": c_to_f(temp_summary["max"]),
        },
        "sky_cover": forecast["skyCover"]["summary"],
        "humidity": forecast["relativeHumidity"]["summary"],
        "rain": {
            "max_probability_percent": forecast[
                "probabilityOfPrecipitation"
            ]["summary"]["max"],
            "expected_inches": mm_to_inches(
                rain_summary["max"]
            ),
        },
        "wind": {
            "avg_mph": kmh_to_mph(wind_summary["avg"]),
            "max_gust_mph": kmh_to_mph(gust_summary["max"]),
            "predominant_direction": current["wind_direction"],
        },
    }


def build_context_for_river(
    river_key: str,
    river_config: Dict[str, Any],
    stocking: Dict[str, Any],
    flies: Dict[str, Any],
) -> Dict[str, Any]:

    weather = safe_load_json(
        f"data/weather/{river_key}.json"
    )

    weather_summary = summarize_weather(weather)
    forecast_breakdown = split_forecast_windows(weather) if weather else {}

    usgs = safe_load_json(
    f"data/usgs/{river_key}.json")

    usgs_summary = build_usgs_summary(usgs)

    return {
        "river_key": river_key,
        "river": river_config,
        "usgs_summary": usgs_summary,
        "weather_summary": weather_summary,
        "forecast_breakdown": forecast_breakdown,
        "stocking": stocking.get(river_key),
        "available_flies": flies,
        "instructions": [
            "Generate a 48-hour trout fishing outlook.",
            "Use only the provided data.",
            "If data is missing, say it is unavailable.",
            "Do not make wading safety claims.",
            "Recommend 3 to 5 flies from available_flies.",
            "Use forecast_breakdown to distinguish day 1 vs day 2 and morning vs afternoon vs evening.",
            "Use SEO-friendly language like fishing report, trout fishing, stocked, hatches, and recommended flies.",
        ],
    }


def main() -> None:
    river_config = load_river_config()

    stocking = safe_load_json(
        "data/stocking/current_stocking.json"
    ) or {}

    flies = load_json(
        "src/troutintel/assets/flies.json"
    )

    for river_key in RIVERS:
        context = build_context_for_river(
            river_key=river_key,
            river_config=river_config[river_key],
            stocking=stocking,
            flies=flies,
        )

        save_json(
            context,
            f"data/llm_context/{river_key}.json",
        )

        print(f"Wrote LLM context for {river_key}")


if __name__ == "__main__":
    main()
