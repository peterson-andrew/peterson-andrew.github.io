import json
from pathlib import Path
from typing import Any, Dict

def load_json(path: str) -> Any:
	return json.loads(
		Path(path).read_text(encoding="utf-8")
		)

def build_llm_input(conditions: Dict[str, Any], files: list[Dict[str, Any]],) -> Dict[str, Any]:
	return {
		"instructions": [
			"Generate a weekly fishing report",
			"Evaluate fishing quality",
			"Do not make wading safety claims",
			"For Chattahoochee tailwaters, do not use flow or gauage height to score fishing quality.",
			"Recommend 305 flies from inventory only.",
		],
		"conditions": conditions,
		"available_flies": flies,
	}

def save_json(data: Dict[str, Any], output_path: str) -> None:
	path = Path(output_path)

	path.parent.mkdir(parents=True, exist_ok=True,)

	path.write_text(json.dumps(data, indent=2), encoding="utf-8",)

def main() -> None:

	conditions = load_json("data/combined/chattahoochee_conditions.json")

	flies = load_json("data/inventory/flies.json")

	llm_input = build_llm_input(conditions, flies,)

	save_json(llm_input, "data/llm_inputs/chattahoochee_llm_input.json",)

if __name__ == "__main__":
	main()