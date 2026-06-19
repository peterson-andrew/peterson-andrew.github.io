from typing import Optional


GA_DNR_STOCKING_PDF_URL = (
    "https://georgiawildlife.com/sites/default/files/wrd/pdf/trout/Weekly_Stocking_Report.pdf"
)


RIVER_MAPPINGS = {
    "Lanier Tailwater": "chattahoochee",
    "Blueridge TW": "toccoa",
    "Blueridge Tailwater": "toccoa",
    "Soque River": "soque",
    "Etowah River": "etowah",
    "Toccoa River (F)": "toccoa"
}


def normalize_waterbody(waterbody: str) -> Optional[str]:
    return RIVER_MAPPINGS.get(waterbody.strip())
