#!/bin/bash
# ICLR follow-up arms (2026-08-17). Preregisters:
#   schema_fix -> docs/iclr-schema-fix-preregister.md
#   gemma_q90  -> docs/iclr-gemma-q90-preregister.md
#   v_trace    -> docs/iclr-v-trace-preregister.md  (v_trace_bn optional)
# Plan: docs/iclr-followup-plan-2026-08-17.md
#
# Usage:
#   e_iclr2.sh chain_qwen   # schema_fix then v_trace (one Qwen pod)
#   e_iclr2.sh gemma_q90    # Gemma pod (or after chain_qwen on the same pod)
#   e_iclr2.sh schema_fix|v_trace|v_trace_bn   # single block
#
# Every w is measured on-pod (measure_c / measure_q / measure_c_schema),
# never copied from a doc. A fresh pod is a NEW stack: each block re-runs
# its own baseline and pairs only within its own db. Never pool with the
# 2026-08-14/15 stacks.
#
# UV_NO_SYNC is not optional — see docs/runpod-api-guide.md §7 (an implicit
# uv sync can swap the pinned torch wheel and break model load).
set -u
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1
cd /workspace/mlkv
BLOCK=${1:?usage: e_iclr2.sh chain_qwen|schema_fix|gemma_q90|v_trace|v_trace_bn}
LOG=/workspace/iclr2_${BLOCK}.log
QWEN=Qwen/Qwen3-4B
GEMMA=google/gemma-3-4b-it
CAP=384
N=100

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

# ---------------------------------------------------------------------------
run_schema_fix() {
  say "=== schema_fix start (hat_w = c_schema + Q90_en, measured on-pod)"
  UV_NO_SYNC=1 uv run python scripts/measure_q.py --models "$QWEN" --langs en \
    | tee -a "$LOG"
  UV_NO_SYNC=1 uv run python scripts/measure_c_schema.py --models "$QWEN" \
    --pads 60,120,200 | tee /tmp/c_schema.txt | tee -a "$LOG"
  for pad in 60 120 200; do
    w=$(awk -v P="$pad" '$2==P {print $7; exit}' /tmp/c_schema.txt)
    [ -n "$w" ] || { say "FATAL: no hat_w for pad $pad"; exit 1; }
    say "schema_fix pad=$pad hat_w=$w"
    run_mlkv --model "$QWEN" --task mrag --langs en --ctx 8k \
      --configs "baseline,snapkv@r0.75,snapkv@r0.75:w${w}" \
      --mrag-instr-pad "$pad" --mrag-tail json \
      --max-items "$N" --max-new-tokens "$CAP" \
      --db results/schema_fix.db
    say "SCHEMA_FIX_PAD${pad}_DONE"
  done
  snap schema_fix
  say ALL_ICLR2_SCHEMA_FIX_DONE
}

# ---------------------------------------------------------------------------
run_gemma_q90() {
  say "=== gemma_q90 start (hat_w = c + Q90, both on the Gemma tokenizer)"
  UV_NO_SYNC=1 uv run python scripts/measure_c.py --models "$GEMMA" \
    --langs en,bn,te | tee /tmp/c_gemma.txt | tee -a "$LOG"
  UV_NO_SYNC=1 uv run python scripts/measure_q.py --models "$GEMMA" \
    --langs en,bn,te --out results/q_percentiles_gemma.json | tee -a "$LOG"
  for lang in en bn te; do
    w=$(UV_NO_SYNC=1 uv run python - "$lang" <<'PY'
import json, sys
from pathlib import Path
lang = sys.argv[1]
c = None
for line in Path("/tmp/c_gemma.txt").read_text().splitlines():
    p = line.split()
    if len(p) >= 6 and p[1] == lang and p[4].isdigit():
        c = int(p[4])
if c is None:
    raise SystemExit(f"no c for {lang}")
rows = json.loads(Path("results/q_percentiles_gemma.json").read_text())
q90 = next(int(r["Q90"]) for r in rows if r["lang"] == lang)
print(c + q90)
PY
)
    [ -n "$w" ] || { say "FATAL: no hat_w for $lang"; exit 1; }
    say "gemma_q90 $lang hat_w=$w"
    run_mlkv --model "$GEMMA" --task mrag --langs "$lang" --ctx 8k \
      --configs "baseline,snapkv@r0.75,snapkv@r0.75:w${w}" \
      --max-items "$N" --max-new-tokens "$CAP" \
      --db results/gemma_q90.db
    say "GEMMA_Q90_${lang}_DONE"
  done
  snap gemma_q90
  say ALL_ICLR2_GEMMA_Q90_DONE
}

# ---------------------------------------------------------------------------
v_trace_lang() {
  # $1 = lang, $2 = space-separated locked offsets
  local lang=$1 offsets=$2
  local c
  c=$(UV_NO_SYNC=1 uv run python scripts/measure_c.py --models "$QWEN" \
    --langs "$lang" | tee -a "$LOG" | awk -v L="$lang" '$2==L {print $5; exit}')
  [ -n "$c" ] || { say "FATAL: no c for $lang"; exit 1; }
  local configs="baseline"
  for off in $offsets; do
    configs="${configs},snapkv@r0.75:w$((c + off))"
  done
  say "v_trace $lang c=$c configs=$configs"
  run_mlkv --model "$QWEN" --task mrag --langs "$lang" --ctx 8k \
    --configs "$configs" \
    --max-items "$N" --max-new-tokens "$CAP" \
    --db results/v_trace.db
  say "V_TRACE_${lang}_DONE"
}

run_v_trace() {
  say "=== v_trace start (te, locked offsets 4 16 32 48 80)"
  v_trace_lang te "4 16 32 48 80"
  snap v_trace
  say ALL_ICLR2_V_TRACE_DONE
}

run_v_trace_bn() {
  say "=== v_trace_bn start (optional; locked offsets 4 16 32 48 76)"
  v_trace_lang bn "4 16 32 48 76"
  snap v_trace
  say ALL_ICLR2_V_TRACE_BN_DONE
}

preflight

case "$BLOCK" in
  schema_fix) run_schema_fix ;;
  gemma_q90) run_gemma_q90 ;;
  v_trace) run_v_trace ;;
  v_trace_bn) run_v_trace_bn ;;
  chain_qwen) run_schema_fix; run_v_trace; say ALL_ICLR2_QWEN_DONE ;;
  *) say "unknown block: $BLOCK"; exit 1 ;;
esac
