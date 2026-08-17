#!/usr/bin/env python3
"""Preregistered §7 stats on cliff_multi. R2, never stored correct.

  uv run --with statsmodels python scripts/iclr_stats.py

Models:
  M_int : correct ~ compressed * blind + (1|item)   # headline
  M_wc  : correct ~ compressed * (w - c)
  M_w   : correct ~ compressed * w
  M_fe  : correct ~ compressed * C(lang)
AIC on the three mean-structure GLMs (item-clustered). Mixed logit if
statsmodels supports it; otherwise GEE / clustered logit + AIC on GLM.
"""
from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mlkv.qa_metrics import containment_match_lenient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "results"
C_LOCK = {"en": 25, "th": 45, "sw": 47, "bn": 107, "te": 167}


def golds(s):
    if not s:
        return []
    s = s.strip()
    if s.startswith("["):
        try:
            v = ast.literal_eval(s)
            if isinstance(v, list):
                return [str(x) for x in v]
        except Exception:
            pass
    return [s]


def r2(out, gold, lang):
    return int(bool(containment_match_lenient(out or "", golds(gold), lang)))


def parse_w(cfg: str) -> float | None:
    if cfg == "baseline":
        return None
    if ":w" in cfg:
        return float(cfg.split(":w")[-1])
    return 64.0


def main() -> None:
    import sqlite3

    import pandas as pd

    con = sqlite3.connect(f"file:{ROOT / 'cliff_multi-final.db'}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT item_id, lang, config, output, answer_gold FROM generations"
    ).fetchall()
    recs = []
    for iid, lang, cfg, out, gold in rows:
        w = parse_w(cfg)
        is_base = cfg == "baseline"
        recs.append(
            {
                "item": iid,
                "lang": lang,
                "config": cfg,
                "y": r2(out, gold, lang),
                "compressed": 0 if is_base else 1,
                "w": 8192.0 if is_base else float(w),
                "c": C_LOCK[lang],
            }
        )
    df = pd.DataFrame(recs)
    df["blind"] = ((df["compressed"] == 1) & (df["w"] < df["c"])).astype(int)
    df["wmc"] = df["w"] - df["c"]
    print("n rows", len(df), "items", df.item.nunique())
    print(
        df[df.compressed == 1]
        .groupby(["lang", "blind"])["y"]
        .mean()
        .unstack()
        .round(3)
    )

    import statsmodels.formula.api as smf

    # blind is 0 unless compressed=1, so compressed:blind ≡ blind.
    # Operational headline: extra damage from 1[w<c] on top of compression.
    m_int = smf.logit("y ~ compressed + blind", data=df).fit(
        disp=False, cov_type="cluster", cov_kwds={"groups": df["item"]}
    )
    print("\n## Headline  y ~ compressed + 1[w<c]  (cluster = item)")
    print("    (interaction compressed:blind is identical to blind)")
    print(m_int.summary().tables[1])
    print("AIC", round(m_int.aic, 1))

    treated = df[df.compressed == 1].copy()
    m_wc = smf.logit("y ~ wmc", data=treated).fit(disp=False)
    m_w = smf.logit("y ~ w", data=treated).fit(disp=False)
    m_fe = smf.logit("y ~ C(lang)", data=treated).fit(disp=False)
    m_b = smf.logit("y ~ blind", data=treated).fit(disp=False)
    print("\n## AIC on compressed rows only (lower better)")
    print("    language FE is the mandatory competitor from the preregister")
    for name, m in [(" (w-c)", m_wc), ("w", m_w), ("lang FE", m_fe), ("blind", m_b)]:
        print(f"  {name:12}  AIC={m.aic:8.1f}  llf={m.llf:9.1f}  k={int(m.df_model)+1}")


if __name__ == "__main__":
    main()
