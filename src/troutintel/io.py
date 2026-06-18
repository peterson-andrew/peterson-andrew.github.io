import json
from pathlib import Path
from typing import Any

def load_json(path: str) -> Any:
  return json.loads(
    Path(path).read_text(
      encoding="utf-8"
    )
  )

def save_json(data: Any, output_path: str,) -> None:
  path = Path(output_path)

  path.parent.mkdir(
    parents=True,
    exist_ok=True,
  )

path.write_text(
  json.dumps(
    data,
    indent=2,
  ),
  encoding="utf-8",
)
