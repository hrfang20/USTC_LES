"""Run with the project's turbpy Python from any working directory."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ustc_les.planning import preflight, read_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/campus_draft.json")
    args = parser.parse_args()
    report = preflight(read_config(args.config), ROOT)
    report["python_executable"] = sys.executable
    output = ROOT / "outputs/preflight.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(report, ensure_ascii=False, indent=2)
    output.write_text(content + "\n", encoding="utf-8")
    print(content)
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
