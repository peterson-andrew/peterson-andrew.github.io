import json
import os
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI

from troutintel.io import load_json, save_json
from troutintel.transforms.report_builder import (
    build_structured_report,
    render_report_html,
)


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


def build_prompt(context: Dict[str, Any]) -> str:
    return f"""
Write ONLY valid JSON.

Do not include markdown.
Do not include HTML.
Do not include extra keys.

Return exactly this object shape:

{{
  "quick_read": "...",
  "best_window": "...",
  "current_conditions": "...",
  "weather_setup": "...",
  "what_this_means": "..."
}}

Rules:
- Use only the provided data.
- Do not invent data.
- Do not make wading safety claims.
- Use angler_analysis as the expert fishing interpretation.
- Keep each field concise.
- quick_read: 2 sentences max.
- best_window: explain why angler_analysis.best_window is best.
- current_conditions: mention USGS water temp, flow, gage height, and turbidity if available.
- weather_setup: mention sky cover, pressure, pressure trend, wind, and rain if available.
- what_this_means: explain trout behavior, positioning, presentation style, and caution notes.

Context JSON:
{json.dumps(context, indent=2)}
"""


def generate_report_text(
    client: OpenAI,
    context: Dict[str, Any],
) -> Dict[str, str]:
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=build_prompt(context),
    )

    return json.loads(response.output_text)


def save_report(
    river_key: str,
    report: Dict[str, Any],
    html: str,
) -> None:
    final_html = f"{html}\n\n{COMMON_SENSE_DISCLAIMER}"

    output_dir = Path(f"data/reports/{river_key}")
    output_dir.mkdir(parents=True, exist_ok=True)

    save_json(
        report,
        f"data/reports/{river_key}/latest.json",
    )

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

        generated_text = generate_report_text(
            client=client,
            context=context,
        )

        report = build_structured_report(
            context=context,
            generated_text=generated_text,
        )

        html = render_report_html(report)

        save_report(
            river_key=river_key,
            report=report,
            html=html,
        )

        print(f"Wrote structured 48-hour outlook for {river_key}")


if __name__ == "__main__":
    main()
