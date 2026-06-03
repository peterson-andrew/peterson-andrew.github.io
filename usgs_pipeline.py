import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

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


async def fetch_json(client: httpx.AsyncClient, url: str, params: Optional[Dict[str, str]] = None,) -> Dict[str, Any]:
    response = await client.get(url, params=params)
    response.raise_for_status()
    
    return response.json()


async def get_usgs_instant_values(client: httpx.AsyncClient, site_id: str, parameter_codes: List[str],) -> Dict[str, Any]:
    params = {
    "format": "json",
    "sites": site_id,
    "parameterCd": ",".join(parameter_codes),
    "siteStatus": "all",
    }
    
    return await fetch_json(client, USGS_IV_URL, params=params)


def normalize_usgs_instant_values(raw_usgs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert USGS-shaped JSON into fishing-report-shaped data.
    """
    result = {
        "site_name": None,
        "site_code": None,
        "readings": {},
    }

    time_series = raw_usgs["value"]["timeSeries"]

    for series in time_series:
        variable = series["variable"]
        variable_code = variable["variableCode"][0]["value"]
        variable_name = variable["variableName"]

        site = series["sourceInfo"]
        result["site_name"] = site["siteName"]
        result["site_code"] = site["siteCode"][0]["value"]

        values = series["values"][0]["value"]

        if not values:
            continue

        latest_value = values[-1]

        reading = {
            "parameter_code": variable_code,
            "name": variable_name,
            "value": float(latest_value["value"]),
            "timestamp": latest_value["dateTime"],
            }

        if variable_code == "00060":
            result["readings"]["flow_cfs"] = reading

        elif variable_code == "00065":
            result["readings"]["gage_height_ft"] = reading

        elif variable_code == "00010":
            temp_c = reading["value"]
            reading["value_c"] = temp_c
            reading["value_f"] = round((temp_c * 9 / 5) + 32, 1)
            result["readings"]["water_temp"] = reading

        elif variable_code == "63680":
            result["readings"]["turbidity"] = reading

        else:
            result["readings"][variable_code] = reading

    return result


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
