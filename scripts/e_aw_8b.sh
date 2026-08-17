#!/bin/bash
# Qwen3-8B scale slice. Spec: session plan 2026-08-15.
# en+bn × {baseline, snapkv@r0.75, snapkv@r0.75:w<c+Q90>}.
# Measure c and Q90 on THIS tokenizer before generate.
set -euo pipefail
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1
export HF_HUB_DISABLE_XET=1
cd /workspace/mlkv
LOG=/workspace/iclr_aw_8b_v2.log
M=Qwen/Qwen3-8B
CAP=384
N=100

say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }

say "=== aw_8b start HEAD $(git rev-parse --short HEAD)"

UV_NO_SYNC=1 uv run python scripts/measure_c.py --models "$M" --langs en,bn \
  | tee /tmp/c8.txt | tee -a "$LOG"
UV_NO_SYNC=1 uv run python scripts/measure_q.py --models "$M" --langs en,bn \
  | tee -a "$LOG"

aw_w() {
  local lang=$1
  python3 - "$lang" <<'PY'
import json, sys
from pathlib import Path
lang = sys.argv[1]
c = None
for line in Path("/tmp/c8.txt").read_text().splitlines():
    p = line.split()
    if len(p) >= 6 and p[1] == lang and p[4].isdigit():
        c = int(p[4])
if c is None:
    raise SystemExit(f"no c for {lang}")
rows = json.loads(Path("results/q_percentiles.json").read_text())
q90 = next(int(r["Q90"]) for r in rows if r["lang"] == lang)
print(c + q90)
PY
}

for lang in en bn; do
  w=$(aw_w "$lang")
  [ -n "$w" ] || { say "FATAL: no w for $lang"; exit 1; }
  say "aw_8b $lang w=$w"
  UV_NO_SYNC=1 uv run mlkv run --model "$M" --task mrag --langs "$lang" --ctx 8k \
    --configs "baseline,snapkv@r0.75,snapkv@r0.75:w${w}" \
    --max-items "$N" --max-new-tokens "$CAP" \
    --db results/autowin_8b.db 2>&1 | tee -a "$LOG"
  say "AW_8B_${lang}_DONE"
done

python3 - <<'PY' >> "$LOG"
import sqlite3
c = sqlite3.connect("results/autowin_8b.db")
c.execute("VACUUM INTO 'results/autowin_8b-snapshot.db'")
n = c.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
print("autowin_8b", n, "rows")
PY
say ALL_ICLR_AW_8B_V2_DONE
