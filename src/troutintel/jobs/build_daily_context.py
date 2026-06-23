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


def build_context_for_river(
    river_key: str,
    river_config: Dict[str, Any],
    stocking: Dict[str, Any],
    flies: Dict[str, Any],
) -> Dict[str, Any]:

    weather = safe_load_json(
        f"data/weather/{river_key}.json"
    )

    return {
        "river_key": river_key,
        "river": river_config,
        "weather": weather,
        "stocking": stocking.get(river_key),
        "available_flies": flies,
        "instructions": [
            "Generate a daily trout fishing report.",
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
