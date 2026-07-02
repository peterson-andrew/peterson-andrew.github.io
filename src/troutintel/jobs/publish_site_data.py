from pathlib import Path
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


def build_river_site_data(
    river_key: str,
    river_config: Dict[str, Any],
) -> Dict[str, Any]:
    report = safe_load_json(
        f"data/reports/{river_key}/latest.json"
    )

    llm_context = safe_load_json(
        f"data/llm_context/{river_key}.json"
    )

    usgs = safe_load_json(
        f"data/usgs/{river_key}.json"
    )

    weather = safe_load_json(
        f"data/weather/{river_key}.json"
    )

    return {
        "river_key": river_key,
        "river": river_config,
        "latest_report": report,
        "llm_context": llm_context,
        "current_conditions": usgs,
        "weather": weather,
    }


def build_homepage_data(
    rivers: Dict[str, Any],
) -> Dict[str, Any]:
    river_cards = []

    for river_key in RIVERS:
        report = safe_load_json(
            f"data/reports/{river_key}/latest.json"
        )

        context = safe_load_json(
            f"data/llm_context/{river_key}.json"
        )

        river_cards.append(
            {
                "river_key": river_key,
                "display_name": rivers[river_key]["display_name"],
                "rating": (
                    report.get("rating")
                    if report
                    else None
                ),
                "best_window": (
                    report.get("best_window")
                    if report
                    else None
                ),
                "stocking": (
                    context.get("stocking")
                    if context
                    else None
                ),
            }
        )

    return {
        "title": "Georgia Trout Fishing",
        "rivers": river_cards,
    }


def main() -> None:
    rivers = load_river_config()

    Path("site_data/rivers").mkdir(
        parents=True,
        exist_ok=True,
    )

    for river_key in RIVERS:
        river_data = build_river_site_data(
            river_key=river_key,
            river_config=rivers[river_key],
        )

        save_json(
            river_data,
            f"site_data/rivers/{river_key}.json",
        )

        print(f"Wrote site data for {river_key}")

    homepage = build_homepage_data(rivers)

    save_json(
        homepage,
        "site_data/homepage.json",
    )

    print("Wrote site_data/homepage.json")


if __name__ == "__main__":
    main()
