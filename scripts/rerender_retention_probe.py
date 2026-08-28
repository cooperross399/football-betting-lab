#!/usr/bin/env python3
"""Regenerate the retention report from the raw responses. Spends nothing.

Historical prices never change, so a cached snapshot is a permanent record and
the report is derived data. That means the report can be improved — better
roll-ups, clearer wording, a distinction nobody had thought of yet — without
paying for the evidence again.

    PYTHONPATH=src python scripts/rerender_retention_probe.py

This is not a convenience. The first version of this report rolled up by
provider key alone and read as though three markets could not be measured,
when their alternate ladders showed that they could. Fixing that would have
been worthless if fixing it meant re-spending 7,280 credits.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.reports import retention_probe as probe_module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    args = parser.parse_args(argv)

    league = league_for(args.league)
    payload_path = OUTPUTS_DIR / league.output_name("retention_probe", ".json")
    cache_dir = RAW_DIR / league.data_dir_segment / probe_module.CACHE_DIRNAME
    if not payload_path.is_file():
        print(f"No probe record at {payload_path}.", file=sys.stderr)
        return 2
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    result = probe_module.rebuild_from_record(
        payload, league, cache_dir=cache_dir
    )
    if not result.successful:
        print(
            "The cache produced no usable probes. The report was not "
            "overwritten.",
            file=sys.stderr,
        )
        return 2

    markdown = OUTPUTS_DIR / league.output_name("retention_probe", ".md")
    markdown.write_text(probe_module.render(result, league), encoding="utf-8")
    payload_path.write_text(
        json.dumps(probe_module.to_json(result, league), indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Rebuilt {markdown} from {len(result.successful)} cached snapshot(s). "
        "No credit was spent."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
