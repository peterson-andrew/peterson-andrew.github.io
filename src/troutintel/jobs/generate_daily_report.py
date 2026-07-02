import json
import os
from pathlib import Path

from openai import OpenAI

from troutintel.io import load_json


RIVERS = [
    "chattahoochee",
    "toccoa",
    "soque",
    "etowah",
    "nantahala",
]


COMMON_SENSE_DISCLAIMER = """
<section>
  <h3>⚠️ Common Sense Disclaimer</h3>
  <p>This report is for entertainment and planning purposes only. Verify dam releases, weather, and local conditions before fishing. Please don’t do something stupid and then sue us because a trout website didn’t make all of your decisions for you.</p>
</section>
""".strip()


def build_prompt(context: dict) -> str:
    return f"""
You are writing a 48-hour trout fishing outlook for GeorgiaTroutFishing.com.

Use only the provided data.

STRICT OUTPUT RULES:
- Use plain HTML only.
- Do not include markdown.
- Do not add, remove, or rename sections.
- Do not include the disclaimer. It will be appended separately.
- Do not make wading safety claims.
- Do not invent data.

DETERMINISTIC FISHING RULES:
- Use angler_analysis.quality_score exactly.
- Use angler_analysis.quality_label exactly.
- Use angler_analysis.best_window exactly.
- Use angler_analysis.recommended_fly_keys as the fly list.
- Use angler_analysis.fly_reasoning to explain each fly.
- Use angler_analysis.caution_notes if present.
- Treat angler_analysis as the expert fishing interpretation.
- Use weather_summary, forecast_breakdown, usgs_summary, and stocking only as supporting evidence.

OUTPUT EXACTLY THIS STRUCTURE:

<h2>[River Name] 48-Hour Fishing Outlook</h2>

<section>
  <h3>Quick Read</h3>
  <p><strong>Rating:</strong> [quality_label] ([quality_score]/10).</p>
  <p>[2 concise sentences summarizing why.]</p>
</section>

<section>
  <h3>Best Window</h3>
  <p><strong>Best window:</strong> [angler_analysis.best_window].</p>
  <p>[1-2 sentences explaining why from forecast_breakdown.]</p>
</section>

<section>
  <h3>Current River Conditions</h3>
  <p>[Mention water temp, flow, gage height, turbidity if available.]</p>
</section>

<section>
  <h3>Weather Setup</h3>
  <p>[Mention sky cover, pressure, pressure trend, wind/rain if available.]</p>
</section>

<section>
  <h3>Recommended Flies</h3>
  <ul>
    <li><strong>[Fly Name]</strong> — [fly_reasoning]</li>
  </ul>
</section>

<section>
  <h3>What This Means</h3>
  <p>[Use expected_trout_behavior, presentation_style, positioning, tactics, and caution_notes.]</p>
</section>

Context JSON:
{json.dumps(context, indent=2)}
"""


def generate_report_html(client: OpenAI, context: dict) -> str:
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=build_prompt(context),
    )
    return response.output_text


def save_report(river_key: str, html: str) -> None:
    final_html = f"{html}\n\n{COMMON_SENSE_DISCLAIMER}"

    output_dir = Path(f"data/reports/{river_key}")
    output_dir.mkdir(parents=True, exist_ok=True)

    Path(f"data/reports/{river_key}/latest.html").write_text(
        final_html,
        encoding="utf-8",
    )

    Path(f"site_snippets/{river_key}_daily_report.html").write_text(
        final_html,
        encoding="utf-8",
    )


def main() -> None:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    for river_key in RIVERS:
        context_path = f"data/llm_context/{river_key}.json"

        if not Path(context_path).exists():
            print(f"Skipping {river_key}: missing context")
            continue

        context = load_json(context_path)
        html = generate_report_html(client=client, context=context)
        save_report(river_key=river_key, html=html)

        print(f"Wrote 48-hour outlook for {river_key}")


if __name__ == "__main__":
    main()
