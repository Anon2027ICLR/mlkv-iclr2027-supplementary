#!/bin/bash
# Depth arm (2026-08-19). Preregister:
#   docs/iclr-depth-preregister.md   (commit before running)
#
# Final n = the ENTIRE TyDiQA-GoldP validation pool: te 669, bn 113.
# The stopping rule is the pool itself -- no free parameter. The windows
# are the shipped AutoWindow integers; the driver re-derives them on-pod
# and aborts on mismatch. A FATAL guard asserts the Q90 estimation split
# (train) shares no item id with the evaluation split (validation).
#
# Usage:
#   e_iclr7.sh chain     # guards, then te, then bn
#   e_iclr7.sh guards|te|bn
#
# UV_NO_SYNC is not optional -- docs/runpod-api-guide.md §7.
set -u
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1
export HF_HUB_DISABLE_XET=1
cd /workspace/mlkv
BLOCK=${1:?usage: e_iclr7.sh chain|guards|te|bn}
LOG=/workspace/iclr7_${BLOCK}.log
QWEN=Qwen/Qwen3-4B
CAP=384

what_of() {
  case "$1" in
    bn) echo 183 ;;
    te) echo 247 ;;
    *) echo "" ;;
  esac
}

n_of() {
  case "$1" in
    bn) echo 113 ;;
    te) echo 669 ;;
    *) echo "" ;;
  esac
}

say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }

preflight() {
  say "=== preflight HEAD $(git rev-parse --short HEAD) UV_NO_SYNC=${UV_NO_SYNC:-unset}"
  if command -v nvidia-smi >/dev/null; then
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader >> "$LOG" 2>&1 || true
  fi
  UV_NO_SYNC=1 python3 - <<'PY' >> "$LOG" 2>&1
import re, subprocess, sys, torch
print("torch", torch.__version__, "torch_cuda", torch.version.cuda,
      "cuda_available", torch.cuda.is_available())
try:
    smi = subprocess.check_output(["nvidia-smi"], text=True, timeout=10)
except Exception as e:
    print("nvidia-smi missing:", e); sys.exit(0)
m = re.search(r"CUDA Version:\s*([0-9.]+)", smi)
if not m or not torch.version.cuda:
    sys.exit(0)
host, wheel = float(m.group(1)), float(".".join(torch.version.cuda.split(".")[:2]))
print(f"host_cuda={host} wheel_cuda={wheel}")
if wheel > host + 0.05:
    print(f"FATAL: torch {torch.__version__} needs CUDA {wheel} > host {host}")
    sys.exit(2)
PY
  rc=$?
  if [ "$rc" = "2" ]; then
    say "CUDA_MISMATCH -- aborting"
    exit 2
  fi
}

run_guards() {
  say "=== guards: pool sizes, id disjointness, shipped integers"
  UV_NO_SYNC=1 uv run python - <<'PY' 2>&1 | tee -a "$LOG"
import sys
from datasets import load_dataset
ds = load_dataset("google-research-datasets/tydiqa", "secondary_task")
EXPECT = {"bengali": 113, "telugu": 669}
for name, want in EXPECT.items():
    val_ids = {r["id"] for r in ds["validation"] if r["id"].startswith(f"{name}-")}
    tr_ids = {r["id"] for r in ds["train"] if r["id"].startswith(f"{name}-")}
    print(f"{name}: validation={len(val_ids)} train={len(tr_ids)} "
          f"overlap={len(val_ids & tr_ids)}")
    if len(val_ids) != want:
        print(f"FATAL: {name} validation pool is {len(val_ids)}, preregister says {want}")
        sys.exit(2)
    if val_ids & tr_ids:
        print(f"FATAL: {name} eval/held-out splits share {len(val_ids & tr_ids)} ids")
        sys.exit(2)
print("guards OK: pools match the preregister, splits are disjoint")
PY
  rc=$?
  if [ "$rc" != "0" ]; then
    say "GUARDS_FAILED -- aborting"
    exit 2
  fi
  UV_NO_SYNC=1 uv run python scripts/measure_q.py --models "$QWEN" \
    --langs bn,te | tee -a "$LOG"
  for lang in bn te; do
    local c w expected
    c=$(UV_NO_SYNC=1 uv run python scripts/measure_c.py --models "$QWEN" \
      --langs "$lang" | tee -a "$LOG" | awk -v L="$lang" '$2==L {print $5; exit}')
    [ -n "$c" ] || { say "FATAL: no c for $lang"; exit 1; }
    w=$(UV_NO_SYNC=1 uv run python - "$lang" "$c" <<'PY'
import json, sys
from pathlib import Path
lang, c = sys.argv[1], int(sys.argv[2])
rows = json.loads(Path("results/q_percentiles.json").read_text())
q90 = next(int(r["Q90"]) for r in rows if r["lang"] == lang)
print(c + q90)
PY
)
    expected=$(what_of "$lang")
    if [ "$w" != "$expected" ]; then
      say "FATAL: on-pod hat_w for $lang is $w, shipped integer is $expected -- drift, do not run"
      exit 1
    fi
    say "guard $lang: c=$c hat_w=$w == shipped $expected"
  done
  say GUARDS_DONE
}

snap() {
  rm -f "results/$1-snapshot.db"
  python3 -c "
import sqlite3
c = sqlite3.connect('results/$1.db')
c.execute(\"VACUUM INTO 'results/$1-snapshot.db'\")
print('$1', c.execute('SELECT COUNT(*) FROM generations').fetchone()[0], 'rows')
" >> "$LOG" 2>&1
}

run_lang() {
  local lang=$1 n w
  n=$(n_of "$lang"); w=$(what_of "$lang")
  say "=== $lang start (full pool n=$n, hat_w=$w)"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs "$lang" \
    --ctx 8k --configs "baseline,snapkv@r0.75,snapkv@r0.75:w${w}" \
    --max-items "$n" --max-new-tokens "$CAP" \
    --db results/depth.db 2>&1 | tee -a "$LOG"
  snap depth
  say "DEPTH_${lang}_DONE"
}

preflight

case "$BLOCK" in
  guards) run_guards ;;
  te) run_lang te ;;
  bn) run_lang bn ;;
  chain) run_guards; run_lang te; run_lang bn; say ALL_ICLR7_CHAIN_DONE ;;
  *) say "unknown block: $BLOCK"; exit 1 ;;
esac
