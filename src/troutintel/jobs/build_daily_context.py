from typing import Any, Dict

from troutintel.config import load_river_config
from troutintel.io import load_json, save_json


RIVERS = [
    "chattahoochee",
    "toccoa",
    "soque",
    "etowah",
    "nantahala",
]


def safe_load_json(path: str) -> Any:
    try:
        return load_json(path)
    except FileNotFoundError:
        return None


def c_to_f(c: float) -> float:
    return round((c * 9 / 5) + 32, 1)


def kmh_to_mph(kmh: float) -> float:
    return round(kmh * 0.621371, 1)


def mm_to_inches(mm: float) -> float:
    return round(mm / 25.4, 2)


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

    return {
        "river_key": river_key,
        "river": river_config,
        "weather_summary": weather_summary,
        "stocking": stocking.get(river_key),
        "available_flies": flies,
        "instructions": [
            "Generate a 48-hour trout fishing outlook.",
            "Use only the provided data.",
            "If data is missing, say it is unavailable.",
            "Do not make wading safety claims.",
            "Recommend 3 to 5 flies from available_flies.",
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
