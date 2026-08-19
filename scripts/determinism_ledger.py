#!/usr/bin/env python3
"""Count the generations this campaign produced more than once, and check
that the repeats are byte-identical to the first run.

Several arms re-ran cells that an earlier store already contained: an
uncompressed baseline, a default-window cell, a rung of a dose ladder.
Those repeats are the campaign's determinism evidence, so the number the
paper quotes for them should be produced by a script rather than counted
by hand.

A generation is keyed by (model, task, lang, config, item_id,
prompt_version). Two config strings name the same treatment when one
requests the default window implicitly and the other names w=64
explicitly; they are folded together. The earliest row for a key by
created_at is the original and every later row is a repeat.

  UV_NO_SYNC=1 uv run python scripts/determinism_ledger.py
"""
from __future__ import annotations

import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"

# Every store the paper draws on. Snapshot copies are excluded: they are
# byte copies of the live file, not re-runs.
STORES = [
    "cliff_multi-final.db", "cliff_en-final.db", "autowin-final.db",
    "autowin_q90.db", "autowin_8b.db", "cliff_gemma.db", "gemma_q90.db",
    "schema-final.db", "schema_fix.db", "v_trace.db", "v_trace_bn.db",
    "llama.db", "instr_first.db", "agnostic.db", "ratio.db",
    "pyramidkv.db", "constant.db", "depth.db",
]

DEFAULT_W = 64


def norm_config(cfg: str) -> str:
    """Fold the implicit default window onto its explicit spelling."""
    m = re.match(r"^(?P<press>\w+)@(?P<budget>[\w.]+)(?::w(?P<w>\d+))?$", cfg)
    if not m:
        return cfg
    w = int(m["w"]) if m["w"] else DEFAULT_W
    return f'{m["press"]}@{m["budget"]}:w{w}'


def main() -> int:
    # key -> list of (created_at, store, output)
    rows: dict[tuple, list] = defaultdict(list)
    for db in STORES:
        path = RES / db
        if not path.exists():
            print(f"  missing store, skipped: {db}")
            continue
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        for model, task, lang, cfg, iid, pv, out, created, stack in con.execute(
            "SELECT model, task, lang, config, item_id, prompt_version, "
            "output, created_at, stack_id FROM generations"
        ):
            key = (model, task, lang, norm_config(cfg), iid, pv)
            rows[key].append((created, db, cfg, out, stack))
        con.close()

    # A repeat within one stack hash supports the paper's same-system claim;
    # a repeat across stack hashes is a separate, stronger observation and is
    # tallied apart so the paper can quote each precisely.
    pair_shared: dict[tuple[str, str, bool], int] = defaultdict(int)
    pair_identical: dict[tuple[str, str, bool], int] = defaultdict(int)
    renamed = renamed_identical = 0
    for key, entries in rows.items():
        if len(entries) < 2:
            continue
        entries.sort(key=lambda e: e[0])
        _, first_store, first_cfg, first_out, first_stack = entries[0]
        for created, store, cfg, out, stack in entries[1:]:
            same = out == first_out
            cross = stack != first_stack
            pair_shared[(first_store, store, cross)] += 1
            pair_identical[(first_store, store, cross)] += same
            if cfg != first_cfg:
                # Same treatment reached under two config spellings: one
                # store asks for the default window implicitly, the other
                # names w=64.
                renamed += 1
                renamed_identical += same

    print(f"{'original store':<26} {'re-run store':<22} {'stack':<6} shared  identical")
    for pair in sorted(pair_shared, key=lambda p: -pair_shared[p]):
        n, k = pair_shared[pair], pair_identical[pair]
        flag = "" if n == k else f"   <-- {n - k} DIFFER"
        tag = "cross" if pair[2] else "same"
        print(f"{pair[0]:<26} {pair[1]:<22} {tag:<6} {n:6} {k:10}{flag}")

    same_n = sum(v for (a, b, c), v in pair_shared.items() if not c)
    same_k = sum(v for (a, b, c), v in pair_identical.items() if not c)
    cross_n = sum(v for (a, b, c), v in pair_shared.items() if c)
    cross_k = sum(v for (a, b, c), v in pair_identical.items() if c)
    print(f"\nsame stack : {same_n} repeats, {same_k} byte-identical "
          f"(the paper's same-system claim)")
    print(f"cross stack: {cross_n} repeats, {cross_k} byte-identical "
          f"(stronger; quoted separately, never pooled)")
    print(f"of the same-stack repeats, {renamed} also cross the "
          f"implicit/explicit spelling of the default window, "
          f"{renamed_identical} byte-identical")
    if same_n != same_k or renamed != renamed_identical:
        print("MISMATCH: a same-stack repeat differs from its original")
        return 1
    if cross_n != cross_k:
        print("note: cross-stack repeats differ, as stack discipline allows")
    else:
        print("every repeated generation reproduces exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
