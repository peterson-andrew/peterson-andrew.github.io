from typing import Any, Dict, List, Optional
import httpx

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
