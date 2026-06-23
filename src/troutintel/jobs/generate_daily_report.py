import json
import os
from pathlib import Path

from openai import OpenAI

from troutintel.config import load_river_config
from troutintel.io import load_json


RIVERS = [
    "chattahoochee",
    "toccoa",
    "soque",
    "etowah",
    "nantahala",
]


def build_prompt(context: dict) -> str:
    return f"""
You are writing a daily trout fishing report for GeorgiaTroutFishing.com.

Use only the provided data.

Rules:
- Do not invent data.
- If data is missing, say it is unavailable.
- Do not make wading safety claims.
- Recommend 3 to 5 flies from the available fly inventory only.
- Keep the report useful, concise, and SEO-friendly.
- Use plain HTML only.
- Do not include markdown.

Context JSON:
{json.dumps(context, indent=2)}
"""


def generate_report_html(client: OpenAI, context: dict) -> str:
    response = client.responses.create(
        model="gpt-5.5-mini",
        input=build_prompt(context),
    )

    return response.output_text


def save_report(river_key: str, html: str) -> None:
    output_dir = Path(f"data/reports/{river_key}")
    output_dir.mkdir(parents=True, exist_ok=True)

    Path(f"data/reports/{river_key}/latest.html").write_text(
        html,
        encoding="utf-8",
    )

    Path(f"site_snippets/{river_key}_daily_report.html").write_text(
        html,
        encoding="utf-8",
    )


def main() -> None:
    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"]
    )

    load_river_config()

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

        print(f"Wrote report for {river_key}")


if __name__ == "__main__":
    main()
