from typing import Any, Dict, List


def clamp_score(score: float) -> float:
    return round(max(0, min(10, score)), 1)


def label_from_score(score: float, light_status: str) -> str:
    if score >= 8:
        return "Very good"
    if score >= 7 and light_status == "bright_high_pressure":
        return "Good but technical"
    if score >= 7:
        return "Good"
    if score >= 5.5:
        return "Fair to good"
    if score >= 4:
        return "Fair"
    return "Tough"


def analyze_water_temp(temp_f: float | None) -> Dict[str, Any]:
    if temp_f is None:
        return {
            "status": "unknown",
            "read": "Water temperature is unavailable.",
            "positioning": [],
            "tactics": [],
            "score_adjustment": 0,
        }

    if temp_f < 45:
        return {
            "status": "cold",
            "read": "Cold water should slow trout down and push them toward deeper, softer holding water.",
            "positioning": ["deep pools", "slow seams", "softer edges"],
            "tactics": ["slow presentations", "small midges", "dead drifts"],
            "score_adjustment": -1.0,
        }

    if 45 <= temp_f <= 62:
        return {
            "status": "ideal",
            "read": "Water temperature is in a favorable trout range.",
            "positioning": ["riffles", "runs", "seams", "structure"],
            "tactics": ["nymphs", "midges", "soft hackles", "opportunistic streamers"],
            "score_adjustment": 2.0,
        }

    if 62 < temp_f <= 67:
        return {
            "status": "warm",
            "read": "Water is warming; trout may favor more oxygenated water.",
            "positioning": ["riffles", "pocket water", "oxygenated runs"],
            "tactics": ["early and late windows", "active nymphs"],
            "score_adjustment": 0.0,
        }

    if 67 < temp_f <= 70:
        return {
            "status": "hot",
            "read": "Water is warm enough to make trout stress a concern.",
            "positioning": ["fast oxygenated water", "deep plunge pools"],
            "tactics": ["early morning only", "shorter sessions"],
            "score_adjustment": -2.0,
        }

    return {
        "status": "very_hot",
        "read": "Water is very warm for trout.",
        "positioning": ["cold-water refuge", "oxygenated water"],
        "tactics": ["consider not targeting trout"],
        "score_adjustment": -4.0,
    }


def analyze_pressure_trend(weather_summary: Dict[str, Any]) -> Dict[str, Any]:
    pressure_trend = weather_summary.get("pressure_trend") or {}
    trend = pressure_trend.get("trend")

    if not trend or trend == "unknown":
        return {
            "status": "unknown",
            "read": "Pressure trend is unavailable.",
            "score_adjustment": 0.0,
        }

    if trend == "falling":
        return {
            "status": "falling",
            "read": "Falling pressure can improve feeding confidence ahead of changing weather.",
            "score_adjustment": 0.8,
        }

    if trend == "rising":
        return {
            "status": "rising",
            "read": "Rising pressure can make trout a little more cautious after a weather change.",
            "score_adjustment": -0.4,
        }

    return {
        "status": "stable",
        "read": "Stable pressure keeps the outlook more condition-dependent than trend-driven.",
        "score_adjustment": 0.0,
    }


def analyze_light_and_pressure(weather_summary: Dict[str, Any]) -> Dict[str, Any]:
    pressure = weather_summary.get("pressure_inhg")
    sky_avg = weather_summary.get("sky_cover", {}).get("avg")

    if pressure is None or sky_avg is None:
        return {
            "status": "unknown",
            "read": "Light and pressure read is unavailable.",
            "positioning": [],
            "tactics": [],
            "score_adjustment": 0.0,
        }

    high_pressure = pressure >= 30.1
    low_clouds = sky_avg < 35

    if high_pressure and low_clouds:
        return {
            "status": "bright_high_pressure",
            "read": "High pressure and low cloud cover make this fishable but technical.",
            "positioning": ["shade", "deeper runs", "undercut banks", "structure"],
            "tactics": ["smaller natural flies", "careful drifts", "less aggressive presentations"],
            "score_adjustment": -1.0,
        }

    if sky_avg >= 60:
        return {
            "status": "cloudy",
            "read": "Higher cloud cover should reduce overhead exposure and may improve fish confidence.",
            "positioning": ["runs", "riffle edges", "banks", "feeding lanes"],
            "tactics": ["soft hackles", "streamers", "nymphs"],
            "score_adjustment": 1.0,
        }

    return {
        "status": "neutral",
        "read": "Light and pressure do not strongly push the outlook either way.",
        "positioning": ["runs", "seams", "structure"],
        "tactics": ["balanced nymph approach"],
        "score_adjustment": 0.0,
    }


def analyze_stocking(stocking: Dict[str, Any] | None) -> Dict[str, Any]:
    if not stocking or not stocking.get("stocked"):
        return {
            "status": "not_recently_stocked",
            "read": "No recent stocking signal is available.",
            "fly_bias": [],
            "score_adjustment": 0.0,
        }

    return {
        "status": "recently_stocked",
        "read": "Recent stocking supports eggs, worms, and attractor nymphs.",
        "fly_bias": ["egg_pattern", "squirmy_worm", "duracell"],
        "score_adjustment": 1.0,
    }


def choose_best_window(context: Dict[str, Any]) -> str:
    breakdown = context.get("forecast_breakdown") or {}
    best = None
    best_score = -999

    for day_key, day in breakdown.items():
        if not isinstance(day, dict):
            continue

        for window_name in ["morning", "afternoon", "evening"]:
            window = day.get(window_name) or {}
            sky_avg = (window.get("sky_cover") or {}).get("avg")
            gust_max = (window.get("wind_gust_mph") or {}).get("max")
            rain_max = (window.get("rain_probability") or {}).get("max")
            temp_max = (window.get("air_temp_f") or {}).get("max")

            score = 0
            if sky_avg is not None:
                if 35 <= sky_avg <= 75:
                    score += 2
                elif sky_avg < 25:
                    score -= 1
            if gust_max is not None:
                if gust_max <= 10:
                    score += 1
                elif gust_max >= 18:
                    score -= 2
            if rain_max is not None:
                if rain_max <= 25:
                    score += 1
                elif rain_max >= 60:
                    score -= 2
            if temp_max is not None and temp_max >= 90:
                score -= 1
            if window_name == "morning":
                score += 1

            if score > best_score:
                best_score = score
                best = f"{day_key} {window_name}"

    return best or "Best window unavailable"


def choose_flies(
    available_flies: Dict[str, Any],
    water_read: Dict[str, Any],
    light_read: Dict[str, Any],
    stocking_read: Dict[str, Any],
) -> List[str]:
    candidates: List[str] = []
    candidates.extend(stocking_read.get("fly_bias", []))

    if water_read.get("status") in ["cold", "ideal"]:
        candidates.extend(["zebra_midge", "pheasant_tail", "haresear"])

    if light_read.get("status") == "bright_high_pressure":
        candidates.extend(["zebra_midge", "pheasant_tail", "haresear"])

    if light_read.get("status") == "cloudy":
        candidates.extend(["woolly_bugger", "duracell"])

    valid = []
    for fly_key in candidates:
        if fly_key in available_flies and fly_key not in valid:
            valid.append(fly_key)

    return valid[:5]


def build_fly_reasoning(fly_keys: List[str]) -> Dict[str, str]:
    reasons = {
        "egg_pattern": "Recent stocking makes eggs a logical confidence fly.",
        "squirmy_worm": "A simple stocked-trout attractor and good dirty-water option.",
        "duracell": "A strong attractor nymph when fish will move a little but are not fully aggressive.",
        "zebra_midge": "Small and natural for clear, pressured, technical conditions.",
        "pheasant_tail": "A reliable natural nymph when trout are feeding but cautious.",
        "haresear": "General-purpose natural nymph for seams and runs.",
        "woolly_bugger": "Useful if clouds, stain, or low light make fish more willing to chase.",
    }

    return {key: reasons.get(key, "Included based on current conditions.") for key in fly_keys}


def build_angler_analysis(context: Dict[str, Any]) -> Dict[str, Any]:
    usgs = context.get("usgs_summary") or {}
    weather_summary = context.get("weather_summary") or {}
    stocking = context.get("stocking")
    available_flies = context.get("available_flies") or {}

    water_read = analyze_water_temp(usgs.get("water_temp_f"))
    light_read = analyze_light_and_pressure(weather_summary)
    pressure_trend_read = analyze_pressure_trend(weather_summary)
    stocking_read = analyze_stocking(stocking)

    recommended_flies = choose_flies(available_flies, water_read, light_read, stocking_read)

    raw_score = (
        5.0
        + water_read.get("score_adjustment", 0)
        + light_read.get("score_adjustment", 0)
        + pressure_trend_read.get("score_adjustment", 0)
        + stocking_read.get("score_adjustment", 0)
    )

    quality_score = clamp_score(raw_score)
    quality_label = label_from_score(quality_score, light_read.get("status"))

    trout_positioning = list(dict.fromkeys(
        water_read.get("positioning", []) + light_read.get("positioning", [])
    ))

    tactics = list(dict.fromkeys(
        water_read.get("tactics", []) + light_read.get("tactics", [])
    ))

    caution_notes = []
    if light_read.get("status") == "bright_high_pressure":
        caution_notes.append("Bright/high-pressure conditions may make fish cover-oriented and less forgiving.")
    if usgs.get("water_temp_f") and usgs["water_temp_f"] > 67:
        caution_notes.append("Warm water may increase trout stress.")

    return {
        "quality_score": quality_score,
        "quality_label": quality_label,
        "best_window": choose_best_window(context),
        "water_temp_read": water_read,
        "light_pressure_read": light_read,
        "pressure_trend_read": pressure_trend_read,
        "stocking_read": stocking_read,
        "expected_trout_behavior": "Expect trout to favor the most comfortable feeding lanes while staying close to cover when light is high.",
        "presentation_style": "Prioritize clean drifts, smaller natural patterns, and stocked-trout attractors where appropriate.",
        "likely_trout_positioning": trout_positioning,
        "recommended_tactics": tactics,
        "recommended_fly_keys": recommended_flies,
        "fly_reasoning": build_fly_reasoning(recommended_flies),
        "caution_notes": caution_notes,
        "reasoning": [
            water_read.get("read"),
            light_read.get("read"),
            pressure_trend_read.get("read"),
            stocking_read.get("read"),
        ],
    }
