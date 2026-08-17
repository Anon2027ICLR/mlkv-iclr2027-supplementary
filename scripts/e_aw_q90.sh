#!/bin/bash
# AutoWindow-Q90 follow-up. Spec: docs/iclr-autowin-q90-preregister.md
# w = c + Q90, locked from measure_c.py + measure_q.py before generate.
set -eu
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1
cd /workspace/mlkv
LOG=/workspace/iclr_aw_q90.log
QWEN=Qwen/Qwen3-4B
CAP=384
N=100

say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }

say "=== aw_q90 start HEAD $(git rev-parse --short HEAD)"

# Print and capture c, Q90, w per lang. Fail if either script is empty.
UV_NO_SYNC=1 uv run python scripts/measure_c.py --models "$QWEN" --langs en,bn,te | tee -a "$LOG"
UV_NO_SYNC=1 uv run python scripts/measure_q.py --models "$QWEN" --langs en,bn,te | tee -a "$LOG"

aw_w() {
  local lang=$1
  UV_NO_SYNC=1 uv run python - "$lang" <<'PY'
import json, sys
from pathlib import Path
lang = sys.argv[1]
# c from the locked 2026-08-14 Qwen table (same measure_c fallback).
C = {"en": 25, "bn": 107, "te": 167}
qpath = Path("results/q_percentiles.json")
rows = json.loads(qpath.read_text())
q90 = next(r["Q90"] for r in rows if r["lang"] == lang)
print(C[lang] + int(q90))
PY
}

for lang in en bn te; do
  w=$(aw_w "$lang")
  [ -n "$w" ] || { say "FATAL: no Q90 w for $lang"; exit 1; }
  say "aw_q90 $lang w=$w"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs "$lang" --ctx 8k \
    --configs "snapkv@r0.75:w${w}" --max-items "$N" --max-new-tokens "$CAP" \
    --db results/autowin_q90.db 2>&1 | tee -a "$LOG"
  say "AW_Q90_${lang}_DONE"
done

python3 - <<'PY' >> "$LOG"
import sqlite3
c = sqlite3.connect("results/autowin_q90.db")
c.execute("VACUUM INTO 'results/autowin_q90-snapshot.db'")
n = c.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
print("autowin_q90", n, "rows")
PY
say ALL_ICLR_AW_Q90_DONE
