from typing import Any, Dict, List


def fly_name(fly_key: str, available_flies: Dict[str, Any]) -> str:
    fly = available_flies.get(fly_key, {})
    return fly.get("name", fly_key.replace("_", " ").title())


def build_structured_report(
    context: Dict[str, Any],
    generated_text: Dict[str, str],
) -> Dict[str, Any]:
    river = context.get("river", {})
    analysis = context.get("angler_analysis", {})
    usgs = context.get("usgs_summary") or {}
    weather = context.get("weather_summary") or {}
    flies = context.get("available_flies") or {}

    recommended_fly_keys = analysis.get("recommended_fly_keys", [])
    fly_reasoning = analysis.get("fly_reasoning", {})

    recommended_flies = [
        {
            "key": fly_key,
            "name": fly_name(fly_key, flies),
            "reason": fly_reasoning.get(fly_key),
        }
        for fly_key in recommended_fly_keys
    ]

    return {
        "river_key": context.get("river_key"),
        "river_name": river.get("display_name"),
        "title": f'{river.get("display_name")} 48-Hour Fishing Outlook',
        "rating": {
            "score": analysis.get("quality_score"),
            "label": analysis.get("quality_label"),
        },
        "best_window": analysis.get("best_window"),
        "current_conditions": usgs,
        "weather_summary": weather,
        "angler_analysis": analysis,
        "recommended_flies": recommended_flies,
        "generated_text": generated_text,
    }


def render_report_html(report: Dict[str, Any]) -> str:
    rating = report.get("rating", {})
    text = report.get("generated_text", {})
    flies = report.get("recommended_flies", [])

    fly_items = "\n".join(
        [
            f'    <li><strong>{fly["name"]}</strong> — {fly.get("reason") or "Recommended for current conditions."}</li>'
            for fly in flies
        ]
    )

    return f"""
<h2>{report.get("title")}</h2>

<section>
  <h3>Quick Read</h3>
  <p><strong>Rating:</strong> {rating.get("label")} ({rating.get("score")}/10).</p>
  <p>{text.get("quick_read", "")}</p>
</section>

<section>
  <h3>Best Window</h3>
  <p><strong>Best window:</strong> {report.get("best_window")}.</p>
  <p>{text.get("best_window", "")}</p>
</section>

<section>
  <h3>Current River Conditions</h3>
  <p>{text.get("current_conditions", "")}</p>
</section>

<section>
  <h3>Weather Setup</h3>
  <p>{text.get("weather_setup", "")}</p>
</section>

<section>
  <h3>Recommended Flies</h3>
  <ul>
{fly_items}
  </ul>
</section>

<section>
  <h3>What This Means</h3>
  <p>{text.get("what_this_means", "")}</p>
</section>
""".strip()
