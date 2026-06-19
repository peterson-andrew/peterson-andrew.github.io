from typing import Any, Dict
from troutintel.io import load_json

RIVER_CONFIG_PATH = "data/config/river_config.json"

def load_river_config() -> Dict[str, Any]:
  return load_json(
    RIVER_CONFIG_PATH
  )

def get_river(river_name: str,) -> Dict[str, Any]:
  rivers = load_river_config()
  return rivers[river_name]
  
