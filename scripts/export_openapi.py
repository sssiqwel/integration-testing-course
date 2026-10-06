"""Сохраняет OpenAPI-спецификацию приложения в openapi/openapi.json."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402

OUT = ROOT / "openapi" / "openapi.json"


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OpenAPI spec written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
