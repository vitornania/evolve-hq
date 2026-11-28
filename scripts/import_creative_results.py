"""Import a local tracker CSV into this HQ project's learning memory."""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("brand", "product", "creative", "window", "source")
OPTIONAL = ("verdict", "metrics", "observation")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    args = parser.parse_args()
    with args.csv_file.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not set(REQUIRED).issubset(reader.fieldnames or []):
            parser.error("Use these required CSV columns: " + ", ".join(REQUIRED))
        rows = []
        for number, row in enumerate(reader, 2):
            record = {key: (row.get(key) or "").strip() for key in REQUIRED + OPTIONAL}
            if not any(record.values()):
                continue
            if not all(record[key] for key in REQUIRED):
                parser.error(f"Row {number} is missing a brand, product, version, date range, or source.")
            rows.append(record)
    body = json.dumps({"version": 1, "records": rows}, ensure_ascii=False, indent=2)
    if len(body.encode()) > 2_000_000:
        parser.error("Keep the export under 2 MB. Put the most useful recent records first.")
    folder = ROOT / ".office"
    folder.mkdir(exist_ok=True)
    temp = folder / "creative-results.tmp"
    temp.write_text(body + "\n", encoding="utf-8")
    temp.replace(folder / "creative-results.json")
    print(f"Imported {len(rows)} creative results into this project's local memory.")


if __name__ == "__main__":
    main()
