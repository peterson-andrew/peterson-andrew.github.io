import asyncio
from pathlib import Path
from typing import Any, Dict

import httpx

from troutintel.config import load_river_config
from troutintel.io import save_json
from troutintel.sources.usgs import (
    get_usgs_instant_values,
    normalize_usgs_instant_values,
)


USGS_PARAMETER_CODES = {
    "flow_cfs": "00060",
    "gage_height_ft": "00065",
    "water_temp_c": "00010",
    "turbidity": "63680",
}


def render_conditions_html(
    river: Dict[str, Any],
    conditions: Dict[str, Any],
) -> str:
    readings = conditions["readings"]

    flow = readings.get("flow_cfs")
    temp = readings.get("water_temp")
    gage = readings.get("gage_height_ft")
    turbidity = readings.get("turbidity")

    return f"""
<section class="river-conditions-card">
  <h2>{river["display_name"]} Current Conditions</h2>
  <p>{conditions["site_name"]}</p>

  <ul>
    <li>Flow: {flow["value"] if flow else "N/A"} CFS</li>
    <li>Water Temp: {temp["value_f"] if temp else "N/A"}°F</li>
    <li>Gauge Height: {gage["value"] if gage else "N/A"} ft</li>
    <li>Turbidity: {turbidity["value"] if turbidity else "N/A"}</li>
  </ul>
</section>
""".strip()


def save_html(html: str, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def build_usgs_json(
    river_key: str,
    river: Dict[str, Any],
    conditions: Dict[str, Any],
) -> Dict[str, Any]:
    readings = conditions.get("readings", {})

    return {
        "river_key": river_key,
        "river_name": river["display_name"],
        "site_name": conditions.get("site_name"),
        "site_id": river["usgs"]["site_id"],
        "readings": readings,
    }


async def process_river(
    client: httpx.AsyncClient,
    river_key: str,
    river: Dict[str, Any],
) -> None:
    site_id = river["usgs"]["site_id"]

    if site_id is None:
        print(f"Skipping {river_key}: no USGS site configured")
        return

    raw_usgs = await get_usgs_instant_values(
        client=client,
        site_id=site_id,
        parameter_codes=list(USGS_PARAMETER_CODES.values()),
    )

    conditions = normalize_usgs_instant_values(raw_usgs)

    html = render_conditions_html(
        river=river,
        conditions=conditions,
    )

    save_html(
        html,
        f"site_snippets/{river_key}_conditions.html",
    )

    usgs_json = build_usgs_json(
        river_key=river_key,
        river=river,
        conditions=conditions,
    )

    save_json(
        usgs_json,
        f"data/usgs/{river_key}.json",
    )

    print(f"Wrote USGS outputs for {river_key}")


async def main() -> None:
    rivers = load_river_config()

    async with httpx.AsyncClient(timeout=20.0) as client:
        tasks = [
            process_river(client, river_key, river)
            for river_key, river in rivers.items()
        ]

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
