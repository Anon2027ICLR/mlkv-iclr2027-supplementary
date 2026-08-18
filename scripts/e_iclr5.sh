#!/bin/bash
# PyramidKV transfer arm (2026-08-18). Preregister:
#   docs/iclr-pyramidkv-preregister.md   (commit before running)
#
# The treatment is the SHIPPED AutoWindow integer, unchanged: 183 (bn),
# 43 (en), 247 (te). c and Q90 are re-measured on-pod as an environment
# check and the block ABORTS on mismatch — a differing value means the
# pod is not reproducing the campaign environment, not a new hat_w.
#
# Usage:
#   e_iclr5.sh chain     # core (en+bn) then te (one pod)
#   e_iclr5.sh core|te   # single block
#
# UV_NO_SYNC is not optional — docs/runpod-api-guide.md §7.
set -u
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1
export HF_HUB_DISABLE_XET=1
cd /workspace/mlkv
BLOCK=${1:?usage: e_iclr5.sh chain|core|te}
LOG=/workspace/iclr5_${BLOCK}.log
QWEN=Qwen/Qwen3-4B
CAP=384
N=100

# The shipped integers under test (paper Table 3 / measured-constants table).
what_of() {
  case "$1" in
    en) echo 43 ;;
    bn) echo 183 ;;
    te) echo 247 ;;
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
    say "CUDA_MISMATCH — aborting (pin the wheel or move the job)"
    exit 2
  fi
  # PyramidKVPress must exist in the installed kvpress and expose the
  # inherited window_size field the ":w" override sets. Log every field so
  # the library defaults this arm rides on are on record.
  UV_NO_SYNC=1 uv run python - <<'PY' >> "$LOG" 2>&1
import dataclasses, sys
try:
    from kvpress import PyramidKVPress
except ImportError as e:
    print(f"FATAL: PyramidKVPress not in this kvpress: {e}")
    sys.exit(2)
fields = {f.name: f.default for f in dataclasses.fields(PyramidKVPress)}
print("PyramidKVPress fields:", fields)
if "window_size" not in fields:
    print("FATAL: no window_size field — the :w override would not apply")
    sys.exit(2)
PY
  rc=$?
  if [ "$rc" = "2" ]; then
    say "PYRAMIDKV_UNAVAILABLE — aborting"
    exit 2
  fi
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

run_mlkv() {
  UV_NO_SYNC=1 uv run mlkv run "$@" 2>&1 | tee -a "$LOG"
}

c_of() {
  UV_NO_SYNC=1 uv run python scripts/measure_c.py --models "$QWEN" \
    --langs "$1" | tee -a "$LOG" | awk -v L="$1" '$2==L {print $5; exit}'
}

check_what() {
  # Recompute hat_w on-pod and require it to equal the shipped integer.
  local lang=$1 expected c w
  expected=$(what_of "$lang")
  [ -n "$expected" ] || { say "FATAL: no shipped integer for $lang"; exit 1; }
  c=$(c_of "$lang")
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
  if [ "$w" != "$expected" ]; then
    say "FATAL: on-pod hat_w for $lang is $w, shipped integer is $expected — environment drift, do not run"
    exit 1
  fi
  say "check_what $lang: c=$c hat_w=$w == shipped $expected"
}

# ---------------------------------------------------------------------------
run_core() {
  say "=== core start (bn hole language + en safe control)"
  UV_NO_SYNC=1 uv run python scripts/measure_q.py --models "$QWEN" \
    --langs en,bn | tee -a "$LOG"
  check_what bn
  check_what en
  run_mlkv --model "$QWEN" --task mrag --langs bn --ctx 8k \
    --configs "baseline,pyramidkv@r0.75,pyramidkv@r0.75:w183" \
    --max-items "$N" --max-new-tokens "$CAP" \
    --db results/pyramidkv.db
  say "PYRAMIDKV_BN_DONE"
  run_mlkv --model "$QWEN" --task mrag --langs en --ctx 8k \
    --configs "baseline,pyramidkv@r0.75,pyramidkv@r0.75:w43" \
    --max-items "$N" --max-new-tokens "$CAP" \
    --db results/pyramidkv.db
  snap pyramidkv
  say ALL_ICLR5_CORE_DONE
}

# ---------------------------------------------------------------------------
run_te() {
  say "=== te start (optional second blind language)"
  UV_NO_SYNC=1 uv run python scripts/measure_q.py --models "$QWEN" \
    --langs te | tee -a "$LOG"
  check_what te
  run_mlkv --model "$QWEN" --task mrag --langs te --ctx 8k \
    --configs "baseline,pyramidkv@r0.75,pyramidkv@r0.75:w247" \
    --max-items "$N" --max-new-tokens "$CAP" \
    --db results/pyramidkv.db
  snap pyramidkv
  say ALL_ICLR5_TE_DONE
}

preflight

case "$BLOCK" in
  core) run_core ;;
  te) run_te ;;
  chain) run_core; run_te; say ALL_ICLR5_CHAIN_DONE ;;
  *) say "unknown block: $BLOCK"; exit 1 ;;
esac
