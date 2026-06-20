from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Dict, List

import httpx
from pypdf import PdfReader

from troutintel.io import save_json
from troutintel.sources.gadnr import (
    GA_DNR_STOCKING_PDF_URL,
    normalize_waterbody,
)


TRACKED_RIVERS = [
    "chattahoochee",
    "toccoa",
    "soque",
    "etowah",
    "nantahala",
]


def download_pdf() -> bytes:
    response = httpx.get(
        GA_DNR_STOCKING_PDF_URL,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.content


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))

    text_parts = []

    for page in reader.pages:
        text_parts.append(page.extract_text())

    return "\n".join(text_parts)


def parse_stocking_rows(text: str):

    rows = []

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    i = 0

    while i < len(lines) - 2:

        line = lines[i]

        if line.count("/") == 2:

            stocking_date = line

            county = lines[i + 1]

            waterbody = lines[i + 2]

            rows.append(
                {
                    "date": stocking_date,
                    "county": county,
                    "waterbody": waterbody,
                }
            )

            i += 3

        else:

            i += 1

    return rows


def build_stocking_data(rows: List[Dict[str, str]]) -> Dict[str, Dict]:
    stocking = {
        river: {
            "stocked": False,
            "last_stocked": None,
            "matched_waterbodies": [],
        }
        for river in TRACKED_RIVERS
    }

    stocking["nantahala"] = {
        "stocked": None,
        "last_stocked": None,
        "matched_waterbodies": [],
        "note": "NC stocking data not integrated yet",
    }

    for row in rows:
        river_key = normalize_waterbody(row["waterbody"])

        if river_key is None:
            continue

        current = stocking[river_key]

        current["stocked"] = True
        current["last_stocked"] = row["date"]
        current["matched_waterbodies"].append(
            {
                "date": row["date"],
                "county": row["county"],
                "waterbody": row["waterbody"],
            }
        )

    return stocking


def render_html(river: str, data: Dict) -> str:
    if data["stocked"] is True:
        status = "Recently Stocked"
    elif data["stocked"] is False:
        status = "Not Recently Stocked"
    else:
        status = "Stocking Data Not Available"

    return f"""
<section class="stocking-card">
  <h3>Stocking Status</h3>
  <p>{status}</p>
  <p>Last Stocked: {data["last_stocked"]}</p>
</section>
""".strip()


def main() -> None:
    pdf_bytes = download_pdf()
    text = extract_pdf_text(pdf_bytes)
    rows = parse_stocking_rows(text)

    stocking = build_stocking_data(rows)

    save_json(
        stocking,
        "data/stocking/current_stocking.json",
    )

    save_json(
        stocking,
        f"data/history/stocking/{date.today().isoformat()}.json",
    )

    for river, data in stocking.items():
        html = render_html(river, data)

        path = Path(
            f"site_snippets/{river}_stocking_status.html"
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            html,
            encoding="utf-8",
        )

    print("Stocking update complete")


if __name__ == "__main__":
    main()
