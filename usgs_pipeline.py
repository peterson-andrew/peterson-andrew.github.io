import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from troutintel.sources.usgs import (
    fetch_json,
    get_usgs_instant_values,
    normalize_usgs_instant_values
)

import httpx


USGS_IV_URL = "https://waterservices.usgs.gov/nwis/iv/"


USGS_SITES = {
"chattahoochee_norcross": {
"site_id": "02335000",
"display_name": "Chattahoochee River at Norcross",
"output_path": "site_snippets/chattahoochee_conditions.html",
},

"chattahoochee_buford_dam": {
"site_id": "02334430",
"display_name": "Chattahoochee River below Buford Dam",
"output_path": "site_snippets/buford_dam_conditions.html",
},
}


USGS_PARAMETER_CODES = {
"flow_cfs": "00060",
"gage_height_ft": "00065",
"water_temp_c": "00010",
"turbidity": "63680",
}

async def get_usgs_conditions_for_site(site_id: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        raw_usgs = await get_usgs_instant_values(
            client=client,
            site_id=site_id,
            parameter_codes=list(USGS_PARAMETER_CODES.values()),
        )

    return normalize_usgs_instant_values(raw_usgs)

def render_usgs_conditions_html(conditions: Dict[str, Any], display_name: str) -> str:
    readings = conditions["readings"]

    flow = readings.get("flow_cfs")
    temp = readings.get("water_temp")
    gage = readings.get("gage_height_ft")
    turbidity = readings.get("turbidity")

    updated_at = None

    for reading in readings.values():
        updated_at = reading.get("timestamp")
        break

    html = f"""
        <section class="river-conditions-card">
        <h2>Current {display_name} Conditions</h2>
        <p class="river-site">{conditions["site_name"]}</p>

        <div class="river-condition-grid">
        <div class="river-condition">
        <span class="label">Flow</span>
        <span class="value">{flow["value"] if flow else "N/A"} CFS</span>
        </div>

        <div class="river-condition">
        <span class="label">Water Temp</span>
        <span class="value">{temp["value_f"] if temp else "N/A"}°F</span>
        </div>

        <div class="river-condition">
        <span class="label">Gauge Height</span>
        <span class="value">{gage["value"] if gage else "N/A"} ft</span>
        </div>

        <div class="river-condition">
        <span class="label">Turbidity</span>
        <span class="value">{turbidity["value"] if turbidity else "N/A"}</span>
        </div>
        </div>

        <p class="river-updated">Updated: {updated_at}</p>
        <p> class="pipeline-updated">
            Pipeline run: {datetime.now(timezone.utc).isoformat()}
        </p>
        </section>
        """.strip()

    return html

def save_html_snippet(html: str, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    site_config = USGS_SITES["chattahoochee_norcross"]

    conditions = asyncio.run(get_usgs_conditions_for_site(site_config["site_id"]))

    html = render_usgs_conditions_html(conditions=conditions, display_name=site_config["display_name"],)

    save_html_snippet(html=html, output_path=site_config["output_path"],)

    print(html)
