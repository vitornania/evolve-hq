#!/usr/bin/env python3
"""Compare a frozen template inventory with a per-template visual review ledger."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


def records(path, *, review=False):
    rows = {}
    with path.open(encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            key = row.get("id") or row.get("creative_id")
            if not isinstance(key, str) or not key.strip() or key in rows:
                raise ValueError(f"{path}:{line_number} needs a unique template ID")
            if review:
                reason = row.get("reason")
                if (row.get("status") not in {"eligible", "excluded", "unavailable"}
                        or not isinstance(reason, str) or not reason.strip()):
                    raise ValueError(f"{path}:{line_number} needs a verdict and reason")
            rows[key] = row
    return rows


def check(inventory, reviews):
    if not inventory:
        raise ValueError("The inventory contains no template records")
    foreign = reviews.keys() - inventory.keys()
    if foreign:
        raise ValueError(f"Review IDs outside the inventory: {', '.join(sorted(foreign)[:10])}")
    pending = sorted(inventory.keys() - reviews.keys())
    counts = Counter(row["status"] for row in reviews.values())
    return {
        "inventoried": len(inventory),
        "reviewed": counts["eligible"] + counts["excluded"],
        "eligible": counts["eligible"],
        "excluded": counts["excluded"],
        "unavailable": counts["unavailable"],
        "pending": len(pending),
        "next_pending_ids": pending[:25],
        "complete_for_inventory": not pending and not counts["unavailable"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("reviews", type=Path)
    args = parser.parse_args()
    try:
        result = check(records(args.inventory), records(args.reviews, review=True))
    except (OSError, ValueError, AttributeError) as exc:
        print(f"Coverage check failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result["complete_for_inventory"] else 2


if __name__ == "__main__":
    sys.exit(main())
