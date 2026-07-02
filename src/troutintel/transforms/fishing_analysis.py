from typing import Any, Dict, List


def analyze_water_temp(temp_f: float | None) -> Dict[str, Any]:
    if temp_f is None:
        return {
            "status": "unknown",
            "read": "Water temperature is unavailable.",
            "positioning": [],
            "tactics": [],
        }

    if temp_f < 45:
        return {
            "status": "cold",
            "read": "Water is cold; expect slower trout and deeper holding behavior.",
            "positioning": ["deep pools", "slow seams", "softer edges"],
            "tactics": ["slow presentations", "small midges", "dead drifts"],
        }

    if 45 <= temp_f <= 62:
        return {
            "status": "ideal",
            "read": "Water temperature is in a strong trout range.",
            "positioning": ["riffles", "runs", "seams", "structure"],
            "tactics": ["nymphs", "midges", "soft hackles", "opportunistic streamers"],
        }

    if 62 < temp_f <= 67:
        return {
            "status": "warm",
            "read": "Water is warming; trout may favor more oxygenated water.",
            "positioning": ["riffles", "pocket water", "oxygenated runs"],
            "tactics": ["early and late windows", "active nymphs", "oxygenated water"],
        }

    if 67 < temp_f <= 70:
        return {
            "status": "hot",
            "read": "Water is warm enough to increase trout stress.",
            "positioning": ["fast oxygenated water", "deep plunge pools"],
            "tactics": ["early morning only", "shorter sessions", "avoid stressing fish"],
        }

    return {
        "status": "very_hot",
        "read": "Water is very warm for trout.",
        "positioning": ["cold-water refuge", "oxygenated water"],
        "tactics": ["consider not targeting trout"],
    }


def analyze_light_and_pressure(
    weather_summary: Dict[str, Any],
) -> Dict[str, Any]:
    pressure = weather_summary.get("pressure_inhg")
    sky_avg = (
        weather_summary
        .get("sky_cover", {})
        .get("avg")
    )

    if pressure is None or sky_avg is None:
        return {
            "status": "unknown",
            "read": "Light and pressure read is unavailable.",
            "positioning": [],
            "tactics": [],
        }

    high_pressure = pressure >= 30.1
    low_clouds = sky_avg < 35

    if high_pressure and low_clouds:
        return {
            "status": "bright_high_pressure",
            "read": "High pressure and low cloud cover may make trout more cautious and cover-oriented.",
            "positioning": ["shade", "deeper runs", "undercut banks", "structure"],
            "tactics": ["smaller natural flies", "careful drifts", "less aggressive presentations"],
        }

    if sky_avg >= 60:
        return {
            "status": "cloudy",
            "read": "Higher cloud cover should reduce overhead exposure and may improve confidence.",
            "positioning": ["runs", "riffle edges", "banks", "feeding lanes"],
            "tactics": ["soft hackles", "streamers", "nymphs"],
        }

    return {
        "status": "neutral",
        "read": "Light and pressure do not strongly favor an aggressive or defensive trout read.",
        "positioning": ["runs", "seams", "structure"],
        "tactics": ["balanced nymph approach"],
    }


def analyze_stocking(stocking: Dict[str, Any] | None) -> Dict[str, Any]:
    if not stocking or not stocking.get("stocked"):
        return {
            "status": "not_recently_stocked",
            "read": "No recent stocking signal is available.",
            "fly_bias": [],
        }

    return {
        "status": "recently_stocked",
        "read": "Recent stocking supports using simple attractors, eggs, and worm patterns.",
        "fly_bias": ["egg_pattern", "squirmy_worm", "duracell"],
    }


def choose_flies(
    available_flies: Dict[str, Any],
    water_read: Dict[str, Any],
    light_read: Dict[str, Any],
    stocking_read: Dict[str, Any],
) -> List[str]:
    candidates: List[str] = []

    candidates.extend(stocking_read.get("fly_bias", []))

    water_status = water_read.get("status")
    light_status = light_read.get("status")

    if water_status in ["cold", "ideal"]:
        candidates.extend(["zebra_midge", "pheasant_tail", "haresear"])

    if light_status == "bright_high_pressure":
        candidates.extend(["zebra_midge", "pheasant_tail", "haresear"])

    if light_status == "cloudy":
        candidates.extend(["woolly_bugger", "duracell", "soft_hackle"])

    valid = []
    for fly_key in candidates:
        if fly_key in available_flies and fly_key not in valid:
            valid.append(fly_key)

    return valid[:5]


def build_angler_analysis(context: Dict[str, Any]) -> Dict[str, Any]:
    usgs = context.get("usgs_summary") or {}
    weather_summary = context.get("weather_summary") or {}
    stocking = context.get("stocking")
    available_flies = context.get("available_flies") or {}

    water_read = analyze_water_temp(
        usgs.get("water_temp_f")
    )

    light_read = analyze_light_and_pressure(
        weather_summary
    )

    stocking_read = analyze_stocking(
        stocking
    )

    recommended_flies = choose_flies(
        available_flies=available_flies,
        water_read=water_read,
        light_read=light_read,
        stocking_read=stocking_read,
    )

    trout_positioning = []
    trout_positioning.extend(water_read.get("positioning", []))
    trout_positioning.extend(light_read.get("positioning", []))

    tactics = []
    tactics.extend(water_read.get("tactics", []))
    tactics.extend(light_read.get("tactics", []))

    return {
        "water_temp_read": water_read,
        "light_pressure_read": light_read,
        "stocking_read": stocking_read,
        "likely_trout_positioning": list(dict.fromkeys(trout_positioning)),
        "recommended_tactics": list(dict.fromkeys(tactics)),
        "recommended_fly_keys": recommended_flies,
        "reasoning": [
            water_read.get("read"),
            light_read.get("read"),
            stocking_read.get("read"),
        ],
    }
