#!/bin/bash
# Second-review response arms (2026-08-17 late). Preregisters:
#   bn_ladder -> docs/iclr-v-trace-preregister.md (completion; predictions unchanged)
#   agnostic  -> docs/iclr-agnostic-baseline-preregister.md
#   ratio     -> docs/iclr-ratio-sweep-preregister.md
# Plan: docs/second-review-response-plan-2026-08-17.md
#
# Usage:
#   e_iclr4.sh chain        # bn_ladder, agnostic, ratio (one pod)
#   e_iclr4.sh bn_ladder|agnostic|agnostic_tova|ratio   # single block
#
# Every w is measured on-pod. A fresh pod is a new stack: every block is
# self-contained (own baselines) and pairs only within its own db.
# UV_NO_SYNC is not optional — docs/runpod-api-guide.md §7.
set -u
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1
export HF_HUB_DISABLE_XET=1
cd /workspace/mlkv
BLOCK=${1:?usage: e_iclr4.sh chain|bn_ladder|agnostic|agnostic_tova|ratio}
LOG=/workspace/iclr4_${BLOCK}.log
QWEN=Qwen/Qwen3-4B
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

c_of() {
  # locked-method c for one language, measured on-pod
  UV_NO_SYNC=1 uv run python scripts/measure_c.py --models "$QWEN" \
    --langs "$1" | tee -a "$LOG" | awk -v L="$1" '$2==L {print $5; exit}'
}

# ---------------------------------------------------------------------------
run_bn_ladder() {
  say "=== bn_ladder start (completes the preregistered bn dose ladder)"
  local c
  c=$(c_of bn)
  [ -n "$c" ] || { say "FATAL: no c for bn"; exit 1; }
  local configs="baseline"
  for off in 4 16 32 48 76; do
    configs="${configs},snapkv@r0.75:w$((c + off))"
  done
  say "bn_ladder c=$c configs=$configs"
  run_mlkv --model "$QWEN" --task mrag --langs bn --ctx 8k \
    --configs "$configs" \
    --max-items "$N" --max-new-tokens "$CAP" \
    --db results/v_trace_bn.db
  snap v_trace_bn
  say ALL_ICLR4_BN_LADDER_DONE
}

# ---------------------------------------------------------------------------
run_agnostic() {
  say "=== agnostic start (Expected Attention at the headline ratio)"
  run_mlkv --model "$QWEN" --task mrag --langs en,bn,te --ctx 8k \
    --configs "baseline,expected@r0.75" \
    --max-items "$N" --max-new-tokens "$CAP" \
    --db results/agnostic.db
  snap agnostic
  say ALL_ICLR4_AGNOSTIC_DONE
}

run_agnostic_tova() {
  say "=== agnostic_tova start (optional second non-window scorer)"
  run_mlkv --model "$QWEN" --task mrag --langs en,bn,te --ctx 8k \
    --configs "tova@r0.75" \
    --max-items "$N" --max-new-tokens "$CAP" \
    --db results/agnostic.db
  snap agnostic
  say ALL_ICLR4_AGNOSTIC_TOVA_DONE
}

# ---------------------------------------------------------------------------
run_ratio() {
  say "=== ratio start (r=0.9375: the predicted window-tax regime)"
  UV_NO_SYNC=1 uv run python scripts/measure_q.py --models "$QWEN" \
    --langs en,bn | tee -a "$LOG"
  for lang in en bn; do
    local c w
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
    say "ratio $lang c=$c hat_w=$w"
    run_mlkv --model "$QWEN" --task mrag --langs "$lang" --ctx 8k \
      --configs "baseline,snapkv@r0.9375,snapkv@r0.9375:w${w},snapkv@r0.9375:w256" \
      --max-items "$N" --max-new-tokens "$CAP" \
      --db results/ratio.db
    say "RATIO_${lang}_DONE"
  done
  snap ratio
  say ALL_ICLR4_RATIO_DONE
}

preflight

case "$BLOCK" in
  bn_ladder) run_bn_ladder ;;
  agnostic) run_agnostic ;;
  agnostic_tova) run_agnostic_tova ;;
  ratio) run_ratio ;;
  chain) run_bn_ladder; run_agnostic; run_ratio; say ALL_ICLR4_CHAIN_DONE ;;
  *) say "unknown block: $BLOCK"; exit 1 ;;
esac
