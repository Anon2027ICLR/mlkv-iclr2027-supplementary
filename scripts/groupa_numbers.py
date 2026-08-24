#!/usr/bin/env python3
"""Group A numbers for the fourth-review writing pass (no GPU).

1. Residual enrichment as proportion tests (Fisher exact): among items
   broken at w-hat (baseline right -> w-hat wrong), the share with the whole
   question inside the window (|Q| <= Q90) vs that share in the pool.
   Cells: 4B te full pool (depth.db), 8B bn (autowin_8b), Llama bn (llama),
   Gemma bn (gemma_q90).
2. V-bin dedup recompute on the te and bn dose ladders (v_trace stores):
   per-bin paired delta with each distinct item counted once (its mean
   treated correctness in-bin vs its baseline), beside the obs-level number.
3. Vietnamese Q50/Q90/Qmax on the held-out split + the V composition of the
   w=64 cell (autowin-final.db) — verifying the banked facts.

  UV_NO_SYNC=1 uv run python scripts/groupa_numbers.py
"""
from __future__ import annotations

import ast
import json
import math
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mlkv.qa_metrics import containment_match_lenient  # noqa: E402

RES = ROOT / "results"
MODELS = {"depth.db": "Qwen/Qwen3-4B", "autowin_8b.db": "Qwen/Qwen3-8B",
          "llama.db": "meta-llama/Llama-3.1-8B-Instruct",
          "gemma_q90.db": "google/gemma-3-4b-it",
          "v_trace.db": "Qwen/Qwen3-4B", "v_trace_bn.db": "Qwen/Qwen3-4B",
          "autowin-final.db": "Qwen/Qwen3-4B"}


def golds(s):
    s = (s or "").strip()
    if s.startswith("["):
        try:
            v = ast.literal_eval(s)
            if isinstance(v, list):
                return [str(x) for x in v]
        except Exception:
            pass
    return [s] if s else []


def load(db):
    con = sqlite3.connect(f"file:{RES / db}?mode=ro", uri=True)
    out = defaultdict(lambda: defaultdict(dict))
    qid = {}
    for iid, lang, cfg, o, g, m in con.execute(
        "SELECT item_id, lang, config, output, answer_gold, meta FROM generations"
    ):
        out[lang][cfg][iid] = bool(
            containment_match_lenient(o or "", golds(g), lang))
        mm = json.loads(m or "{}")
        if "qid" in mm:
            qid[iid] = mm["qid"]
    con.close()
    return out, qid


def fisher_exact_p(a, b, c, d):
    n = a + b + c + d
    r1, c1 = a + b, a + c

    def hyp(x):
        return (math.comb(c1, x) * math.comb(n - c1, r1 - x)) / math.comb(n, r1)

    p_obs = hyp(a)
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    return min(1.0, sum(hyp(x) for x in range(lo, hi + 1)
                        if hyp(x) <= p_obs * (1 + 1e-9)))


def qlens_for(db, lang, qids):
    from datasets import load_dataset
    from transformers import AutoTokenizer
    from mlkv.tasks.mrag import TYDIQA_LANGS, XQUAD_LANGS

    tok = AutoTokenizer.from_pretrained(MODELS[db])
    out = {}
    if lang in TYDIQA_LANGS:
        ds = load_dataset("google-research-datasets/tydiqa", "secondary_task")
        rows = [r for r in ds["validation"]
                if r["id"].startswith(f"{TYDIQA_LANGS[lang]}-")]
    else:
        rows = list(load_dataset("google/xquad", f"xquad.{lang}",
                                 split="validation"))
    for r in rows:
        if r["id"] in qids:
            out[r["id"]] = len(tok.encode(r["question"], add_special_tokens=False))
    missing = qids - set(out)
    if missing:
        raise ValueError(f"{db}/{lang}: {len(missing)} qids missing")
    return out


# ---- 1. residual enrichment, proportion-test form -----------------------
print("## 1. Residual enrichment: |Q| <= Q90 (question fully visible at w-hat)")
print("   among broken (base right -> w-hat wrong) vs pool; Fisher exact\n")
CELLS = [  # db, lang, w-hat config, Q90 on that tokenizer
    ("depth.db", "te", "snapkv@r0.75:w247", 80),
    ("autowin_8b.db", "bn", "snapkv@r0.75:w183", 76),
    ("llama.db", "bn", "snapkv@r0.75:w212", 87),
    ("gemma_q90.db", "bn", "snapkv@r0.75:w50", 18),
]
for db, lang, cfg, q90 in CELLS:
    S, qid = load(db)
    base, comp = S[lang]["baseline"], S[lang][cfg]
    pool = sorted(set(base) & set(comp))
    broken = [i for i in pool if base[i] and not comp[i]]
    ql = qlens_for(db, lang, {qid[i] for i in pool})
    vis = lambda i: ql[qid[i]] <= q90  # noqa: E731
    a = sum(1 for i in broken if vis(i)); b = len(broken) - a
    rest = [i for i in pool if i not in broken]
    c = sum(1 for i in rest if vis(i)); d = len(rest) - c
    p = fisher_exact_p(a, b, c, d)
    print(f"  {db:15} {lang} {cfg:22} broken {a}/{len(broken)} "
          f"({100*a/len(broken):.0f}%) vs pool {a+c}/{len(pool)} "
          f"({100*(a+c)/len(pool):.0f}%)  Fisher p={p:.3f}")

# ---- 2. V-bin dedup recompute -------------------------------------------
print("\n## 2. V-bin dedup recompute (dose ladders; item counted once per bin)")
C_OF = {"te": 167, "bn": 107}
BINS = [(0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0), (1.0, 1.01)]
for db, lang in (("v_trace.db", "te"), ("v_trace_bn.db", "bn")):
    S, qid = load(db)
    cell = S[lang]
    base = cell["baseline"]
    wcfgs = [(int(cfg.split(":w")[1]), cfg) for cfg in cell if ":w" in cfg]
    ql = qlens_for(db, lang, {qid[i] for i in base})
    c = C_OF[lang]
    print(f"\n  {db} {lang} (c={c}, rungs={sorted(w for w,_ in wcfgs)})")
    print(f"  {'bin':12} {'obs':>4} {'d_obs':>7} {'items':>6} {'d_item':>7}")
    for lo, hi in BINS:
        obs = []  # (item, treated_correct)
        for w, cfg in wcfgs:
            for i, ok in cell[cfg].items():
                if i not in base:
                    continue
                v = max(0.0, min(1.0, (w - c) / ql[qid[i]]))
                if (lo <= v < hi) or (hi > 1.0 and v == 1.0):
                    obs.append((i, ok))
        if not obs:
            continue
        d_obs = 100 * (sum(ok for _, ok in obs) / len(obs)
                       - sum(base[i] for i, _ in obs) / len(obs))
        per = defaultdict(list)
        for i, ok in obs:
            per[i].append(ok)
        d_item = 100 * (sum(sum(v) / len(v) for v in per.values()) / len(per)
                        - sum(base[i] for i in per) / len(per))
        label = "V=1" if lo >= 1.0 else f"{lo}<=V<{hi}"
        print(f"  {label:12} {len(obs):>4} {d_obs:>+7.1f} {len(per):>6} "
              f"{d_item:>+7.1f}")

# ---- 3. Vietnamese ------------------------------------------------------
print("\n## 3. Vietnamese: held-out percentiles and the w=64 cell composition")
from transformers import AutoTokenizer  # noqa: E402
from datasets import load_dataset  # noqa: E402
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-4B")
rows = list(load_dataset("google/xquad", "xquad.vi", split="validation"))
held = rows[100:]
ls = sorted(len(tok.encode(r["question"], add_special_tokens=False)) for r in held)
q50 = ls[len(ls) // 2]
q90 = ls[int(0.9 * len(ls))]
print(f"  held-out n={len(ls)}  Q50={q50}  Q90={q90}  Qmax={ls[-1]}")
S, qid = load("autowin-final.db")
base, w64 = S["vi"]["baseline"], S["vi"]["snapkv@r0.75"]
ql = qlens_for("autowin-final.db", "vi", {qid[i] for i in base})
c_vi = 39
slack = 64 - c_vi
nv = sum(1 for i in base if ql[qid[i]] > slack)
broken = [i for i in base if base[i] and not w64[i]]
bv = sum(1 for i in broken if ql[qid[i]] > slack)
print(f"  w=64 (c={c_vi}, slack={slack}): V<1 items {nv}/100; broken "
      f"{len(broken)}, of which V<1: {bv}")
