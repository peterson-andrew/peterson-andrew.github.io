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

Primary rule:
- Use angler_analysis as the primary fishing interpretation.
- Treat angler_analysis as the expert angler's conclusions.
- Do not override angler_analysis unless required data is clearly missing.
- Use weather_summary, forecast_breakdown, usgs_summary, and stocking only as supporting evidence.

Rules:
- Do not invent data.
- If data is missing, say it is unavailable.
- Do not make wading safety claims.
- Recommend 3 to 5 flies from the available fly inventory only.
- Prefer flies listed in angler_analysis.recommended_fly_keys.
- Use forecast_breakdown to compare day 1 vs day 2 and morning vs afternoon vs evening.
- Mention current river conditions from usgs_summary when available.
- Mention stocking if stocking data is available.
- Keep the report useful, concise, and SEO-friendly.
- Use plain HTML only.
- Do not include markdown.
- Do not include the disclaimer. It will be appended separately.

Required sections:
<h2>[River Name] 48-Hour Fishing Outlook</h2>
<h3>Quick Read</h3>
<h3>Best Windows</h3>
<h3>Conditions Breakdown</h3>
<h3>Recommended Flies</h3>
<h3>What This Means</h3>

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
    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"]
    )

    for river_key in RIVERS:
        context_path = f"data/llm_context/{river_key}.json"

        if not Path(context_path).exists():
            print(f"Skipping {river_key}: missing context")
            continue

        context = load_json(context_path)

        html = generate_report_html(
            client=client,
            context=context,
        )

        save_report(
            river_key=river_key,
            html=html,
        )

        print(f"Wrote 48-hour outlook for {river_key}")


if __name__ == "__main__":
    main()
