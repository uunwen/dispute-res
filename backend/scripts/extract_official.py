import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SRC_DIR = Path(__file__).resolve().parents[1] / "data" / "ryde-Dispute-Resolution-Policy-v2.1"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "official"

_JSON_FENCE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)


def extract_json_block(text: str) -> dict:
    m = _JSON_FENCE.search(text)
    if m is None:
        raise ValueError("no ```json fence found")
    return json.loads(m.group(1))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(SRC_DIR.iterdir()):
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        if "```json" not in text:
            continue
        data = extract_json_block(text)
        ticket = data.get("dispute_ticket") or {}
        dispute_id = ticket.get("dispute_id")
        if not dispute_id:
            raise ValueError(f"{path.name}: missing dispute_ticket.dispute_id")
        out = OUT_DIR / f"{dispute_id}.json"
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{path.name} -> {out.name}")


if __name__ == "__main__":
    main()
