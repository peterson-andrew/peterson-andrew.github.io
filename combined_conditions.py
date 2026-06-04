import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from nws_pipeline import get_buford_dam_weather_bundle, normalize_current_weather
from usgs_pipeline import get_usgs_conditions_for_site, USGS_SITES


def build_fishing_conditions(weather: Dict[str, Any], river: Dict[str, Any], river_display_name: str,) -> Dict[str, Any]:

	return {
		"generated_at_utc": datetime.now(timezone.utc).isoformat(),
		"river": river_display_name,
		"weather": weather,
		"river_conditions": river,
	}


def save_json(data: Dict[str, Any], output_path: str) -> None:

	path = Path(output_path)
	path.parent.mkdir(parents=True, exist_ok=True)

	path.write_text(
		json.dumps(data, indent=2),
		encoding="utf-8",
	)


async def main() -> None:
	site_config = USGS_SITES["chattahoochee_norcross"]

	weather_bundle = await get_buford_dam_weather_bundle()
	weather = normalize_current_weather(weather_bundle)

	river = await get_usgs_conditions_for_site(site_config["site_id"])

	fishing_conditions = build_fishing_conditions(
		weather=weather,
		river=river,
		river_display_name=site_config["display_name"],
	)

	timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
	
	save_json(
		data=fishing_conditions,
		output_path="data/combined/chattahoochee_conditions.json",
	)

	save_json(
		data=fishing_conditions,
		output_path=f"data/history/chattahoochee/{timestamp}.json",
	)

	print(json.dumps(fishing_conditions, indent=2))


if __name__ == "__main__":
	asyncio.run(main())
	
