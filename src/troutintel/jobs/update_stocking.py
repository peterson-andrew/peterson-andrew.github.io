from datetime import date
from pathlib import Path

from troutintel.io import save_json


TRACKED_RIVERS = [
    "chattahoochee",
    "toccoa",
    "soque",
    "etowah",
    "nantahala",
]


def build_stocking_data():

    # Temporary until we automate PDF parsing

    stocked = {
        "chattahoochee": {
            "stocked": True,
            "last_stocked": "2026-06-08",
        },

        "toccoa": {
            "stocked": True,
            "last_stocked": "2026-06-09",
        },

        "soque": {
            "stocked": True,
            "last_stocked": "2026-06-09",
        },

        "etowah": {
            "stocked": True,
            "last_stocked": "2026-06-11",
        },

        "nantahala": {
            "stocked": None,
            "last_stocked": None,
        },
    }

    return stocked


def render_html(river: str, data: dict) -> str:

    if data["stocked"] is True:

        status = "✅ Recently Stocked"

    elif data["stocked"] is False:

        status = "❌ Not Recently Stocked"

    else:

        status = "ℹ️ Stocking Data Not Available"

    return f"""
<section class="stocking-card">

<h3>Stocking Status</h3>

<p>{status}</p>

<p>Last Stocked: {data['last_stocked']}</p>

</section>
""".strip()


def main():

    stocking = build_stocking_data()

    save_json(
        stocking,
        "data/stocking/current_stocking.json",
    )

    for river, data in stocking.items():

        html = render_html(
            river,
            data,
        )

        path = (
            f"site_snippets/"
            f"{river}_stocking_status.html"
        )

        Path(path).write_text(
            html,
            encoding="utf-8",
        )

    print(
        "Stocking update complete"
    )


if __name__ == "__main__":

    main()
