"""
Full-scale dataset pull across the 5 protein-powder categories, via the live
DSLD API (labellens/dsld.py + labellens/taxonomy.py — unmodified).

Strategy (see README / commit message for the reasoning): dedupe to distinct
formulas rather than pulling every raw label ID.

  1. Exact-duplicate collapse, all categories: DSLD re-lists the same
     (brand, fullName) under multiple label IDs (resubmissions, package-size
     variants that didn't change the label name). Collapse those to one.
  2. Whey-specific cap: even after (1), whey has far more distinct
     brand+flavor combinations than the other four categories combined
     (1,159 raw vs. 40/115/125/178). Capped at WHEY_CAP, sampled round-robin
     across brands so one prolific brand doesn't crowd out the rest.

Casein/collagen/pea/plant are pulled in full after exact-dedup — their real
totals are small enough that shrinking them further would be lossy, not
tidy.

Crash-resilient: writes a checkpoint to data/dataset_full.partial.json every
CHECKPOINT_EVERY labels, and logs progress to stderr.

    python build_dataset_full.py
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from labellens.dsld import CITATION, DSLDClient, DSLDError, parse_label
from labellens.schema import Dataset
from labellens.taxonomy import coverage, unmapped

KEYWORDS = {
    "whey": "whey protein",
    "plant": "plant protein",
    "pea": "pea protein",
    "casein": "casein protein",
    "collagen": "collagen protein",
}

WHEY_CAP = 150
CHECKPOINT_EVERY = 25
OUT_PATH = Path("data/dataset_full.json")
CHECKPOINT_PATH = Path("data/dataset_full.partial.json")

MAX_RETRIES = 4
BACKOFF_BASE = 5.0  # seconds


def norm_key(brand: str, name: str) -> tuple[str, str]:
    return (brand.strip().lower(), name.strip().lower())


def collect_candidates(client: DSLDClient, keyword: str) -> list[dict]:
    """
    Page through browse-products for `keyword`, returning every hit as
    {"id": int, "brand": str, "name": str}. Stops when the API returns no
    more hits or we've collected `total.value` items.
    """
    out: list[dict] = []
    page = 1
    total = None
    while True:
        payload = _with_retry(lambda: client.browse_products(keyword, size=50, page=page))
        if total is None:
            total = (payload.get("total") or {}).get("value")
        hits = payload.get("hits", [])
        if not hits:
            break
        for hit in hits:
            src = hit.get("_source", {})
            try:
                dsld_id = int(hit["_id"])
            except (KeyError, TypeError, ValueError):
                continue
            out.append(
                {
                    "id": dsld_id,
                    "brand": src.get("brandName") or "",
                    "name": src.get("fullName") or "",
                }
            )
        page += 1
        if total is not None and len(out) >= total:
            break
    return out


def dedupe(candidates: list[dict]) -> list[dict]:
    """Collapse exact (brand, fullName) duplicates, keeping first occurrence."""
    seen: set[tuple[str, str]] = set()
    result = []
    for c in candidates:
        key = norm_key(c["brand"], c["name"])
        if key in seen:
            continue
        seen.add(key)
        result.append(c)
    return result


def cap_round_robin(items: list[dict], cap: int) -> list[dict]:
    """Cap `items` to `cap` entries, sampling round-robin across brands so no
    single brand dominates."""
    if len(items) <= cap:
        return items
    by_brand: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        by_brand[item["brand"].strip().lower() or "?"].append(item)
    brands = list(by_brand.keys())
    out: list[dict] = []
    i = 0
    while len(out) < cap:
        progressed = False
        for b in brands:
            if by_brand[b]:
                out.append(by_brand[b].pop(0))
                progressed = True
                if len(out) >= cap:
                    break
        if not progressed:
            break
        i += 1
    return out


def _with_retry(fn):
    delay = BACKOFF_BASE
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn()
        except DSLDError as exc:
            msg = str(exc)
            transient = "429" in msg or "timed out" in msg.lower() or "503" in msg
            if attempt == MAX_RETRIES or not transient:
                raise
            print(f"    ! transient error (attempt {attempt}/{MAX_RETRIES}): {exc}", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
    raise DSLDError("unreachable")


def build_selection() -> dict[str, list[dict]]:
    client = DSLDClient()
    selection: dict[str, list[dict]] = {}
    for category, keyword in KEYWORDS.items():
        candidates = collect_candidates(client, keyword)
        deduped = dedupe(candidates)
        print(
            f"  {category:<10} raw={len(candidates):<5} distinct={len(deduped):<5}",
            file=sys.stderr,
        )
        if category == "whey" and len(deduped) > WHEY_CAP:
            deduped = cap_round_robin(deduped, WHEY_CAP)
            print(f"  {category:<10} capped to {len(deduped)}", file=sys.stderr)
        selection[category] = deduped
    return selection


def fetch_all(selection: dict[str, list[dict]]) -> Dataset:
    client = DSLDClient()
    dataset = Dataset(
        generated=datetime.now(timezone.utc).isoformat(),
        query="whey/plant/pea/casein/collagen protein (deduped full pull)",
    )

    all_items = [
        (category, item) for category, items in selection.items() for item in items
    ]
    total = len(all_items)
    print(f"\nfetching {total} labels\n", file=sys.stderr)

    failures: list[tuple[int, str]] = []
    for i, (category, item) in enumerate(all_items, 1):
        dsld_id = item["id"]
        try:
            raw = _with_retry(lambda: client.label(dsld_id))
            dataset.products.append(parse_label(raw))
        except (DSLDError, KeyError, ValueError) as exc:
            print(f"  ! {category} {dsld_id}: {exc}", file=sys.stderr)
            failures.append((dsld_id, str(exc)))
            continue

        if i % CHECKPOINT_EVERY == 0 or i == total:
            print(f"  {i}/{total}  ({category}, id={dsld_id})", file=sys.stderr)
            CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
            CHECKPOINT_PATH.write_text(
                json.dumps(dataset.model_dump(mode="json"), indent=2, default=str)
            )

    if failures:
        print(f"\n{len(failures)} labels failed to fetch/parse:", file=sys.stderr)
        for dsld_id, msg in failures[:20]:
            print(f"    {dsld_id}: {msg}", file=sys.stderr)

    return dataset


def report(dataset: Dataset) -> str:
    s = dataset.summary()
    by_cat_brand = defaultdict(set)
    for p in dataset.products:
        by_cat_brand[p.brand].add(p.dsld_id)

    out = [
        "",
        "=" * 70,
        f"  generated        {dataset.generated[:19]}Z",
        f"  products         {s['total']}  ({s['on_market']} on market)",
        f"  brands           {s['brands']}",
        "",
        "  TRUST SIGNALS (on-market only)",
        f"    independently certified      {s['with_certification']}",
        f"    batch-tested, banned subs    {s['batch_tested']}",
        f"    implies approval, unverified {s['implies_approval_only']}   <- FDA/GMP claim, no real cert",
        "",
        "  INGREDIENT FLAGS",
        f"    contains artificial sweetener {s['with_artificial_sweetener']}",
        "",
        "  TAXONOMY COVERAGE",
        f"    {coverage()}",
    ]
    gaps = unmapped(30)
    if gaps:
        out += ["", f"  TOP UNMAPPED NAMES ({len(gaps)} distinct shown, most frequent first)"]
        for name, count in gaps:
            out.append(f"    {count:>4}x  {name}")
    out += ["=" * 70, f"  source: {CITATION}", ""]
    return "\n".join(out)


def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("collecting candidate label IDs per category...", file=sys.stderr)
    selection = build_selection()

    total_selected = sum(len(v) for v in selection.values())
    print(f"\ntotal selected for fetch: {total_selected}\n", file=sys.stderr)

    dataset = fetch_all(selection)

    OUT_PATH.write_text(json.dumps(dataset.model_dump(mode="json"), indent=2, default=str))
    print(f"\nsaved: {OUT_PATH}", file=sys.stderr)

    print(report(dataset))
    return 0


if __name__ == "__main__":
    sys.exit(main())
