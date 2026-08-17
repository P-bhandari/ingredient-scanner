"""
Ingestion CLI.

    python -m labellens.ingest --keyword "whey protein" --limit 100
    python -m labellens.ingest --keyword "plant protein" --limit 100 --out plant.json
    python -m labellens.ingest --report data/whey_protein.json

Respects DSLD rate limits (self-throttled, disk-cached). Re-running is cheap
because every response is cached under .cache/dsld/.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .dsld import CITATION, DSLDClient, DSLDError, parse_label
from .schema import Category, Dataset
from .taxonomy import coverage, unmapped

DEFAULT_KEYWORDS = [
    "whey protein",
    "plant protein",
    "pea protein",
    "casein protein",
    "collagen protein",
]


def build(keyword: str, limit: int, api_key: str | None = None) -> Dataset:
    client = DSLDClient(api_key=api_key)
    dataset = Dataset(
        generated=datetime.now(timezone.utc).isoformat(),
        query=keyword,
    )

    ids = list(client.iter_ids(keyword, limit=limit))
    print(f"  {len(ids)} label ids for {keyword!r}", file=sys.stderr)

    for i, dsld_id in enumerate(ids, 1):
        try:
            dataset.products.append(parse_label(client.label(dsld_id)))
        except (DSLDError, KeyError, ValueError) as exc:
            print(f"  ! {dsld_id}: {exc}", file=sys.stderr)
            continue
        if i % 25 == 0:
            print(f"  {i}/{len(ids)}", file=sys.stderr)

    return dataset


def report(dataset: Dataset) -> str:
    s = dataset.summary()
    out = [
        "",
        f"  query            {dataset.query!r}",
        f"  generated        {dataset.generated[:19]}Z",
        "",
        f"  products         {s['total']}  ({s['on_market']} on market)",
        f"  brands           {s['brands']}",
        "",
        "  TRUST SIGNALS (on-market only)",
        f"    independently certified      {s['with_certification']}",
        f"    batch-tested, banned subs    {s['batch_tested']}",
        f"    implies approval, unverified {s['implies_approval_only']}   <- the pattern worth flagging",
        "",
        "  INGREDIENT FLAGS",
        f"    contains artificial sweetener {s['with_artificial_sweetener']}",
    ]

    live = [p for p in dataset.products if not p.off_market]
    with_protein = [p for p in live if p.protein_pct_by_weight is not None]
    if with_protein:
        ranked = sorted(
            with_protein,
            key=lambda p: p.protein_pct_by_weight or 0,
            reverse=True,
        )
        out += ["", "  HIGHEST PROTEIN BY WEIGHT"]
        for p in ranked[:8]:
            pct = p.protein_pct_by_weight
            out.append(
                f"    {pct:>5.1f}%  {p.macros.protein_g:>5.1f}g  "
                f"{p.brand[:20]:<20}  {p.name[:44]}"
            )

    prop = [p for p in live if p.has_proprietary_blend]
    if prop:
        out += ["", f"  PROPRIETARY BLENDS ({len(prop)}) — per-ingredient doses hidden"]
        for p in prop[:5]:
            out.append(f"    {p.brand[:20]:<20}  {p.name[:50]}")

    gaps = unmapped(12)
    if gaps:
        cov = coverage()
        out += [
            "",
            f"  TAXONOMY GAPS  ({cov['unmapped_seen']} distinct unmapped names)",
        ]
        for name, count in gaps:
            out.append(f"    {count:>4}x  {name[:60]}")

    out += ["", f"  source: {CITATION}", ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="labellens.ingest")
    p.add_argument("--keyword", action="append", help="Repeatable. Defaults to a standard set.")
    p.add_argument("--limit", type=int, default=100, help="Max labels per keyword")
    p.add_argument("--out", type=Path, help="Output JSON path")
    p.add_argument("--outdir", type=Path, default=Path("data"))
    p.add_argument("--api-key", help="data.gov key for the 10k/hr limit")
    p.add_argument("--report", type=Path, help="Print a report from a saved dataset")
    args = p.parse_args(argv)

    if args.report:
        dataset = Dataset.model_validate(json.loads(args.report.read_text()))
        print(report(dataset))
        return 0

    keywords = args.keyword or DEFAULT_KEYWORDS
    args.outdir.mkdir(parents=True, exist_ok=True)

    for keyword in keywords:
        print(f"\n{keyword}", file=sys.stderr)
        dataset = build(keyword, args.limit, args.api_key)
        path = args.out or args.outdir / f"{keyword.replace(' ', '_')}.json"
        path.write_text(json.dumps(dataset.model_dump(mode="json"), indent=2, default=str))
        print(report(dataset))
        print(f"  saved: {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
