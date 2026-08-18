#!/bin/bash
# Reviewer-3 response arm (2026-08-18). Preregister:
#   docs/iclr-constant-and-ranking-preregister.md   (commit before running)
#
# One store, three languages, three configs: the constant w=256 at the
# headline ratio (W1/Q1) and the random-eviction ranking control (W6/Q5),
# plus a zero-generation pool check for the W4 depth extension.
#
# Usage:
#   e_iclr6.sh chain        # pool_check, then the 900-generation block
#   e_iclr6.sh pool_check|main
#
# UV_NO_SYNC is not optional — docs/runpod-api-guide.md §7.
set -u
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1
export HF_HUB_DISABLE_XET=1
cd /workspace/mlkv
BLOCK=${1:?usage: e_iclr6.sh chain|pool_check|main}
LOG=/workspace/iclr6_${BLOCK}.log
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
    say "CUDA_MISMATCH — aborting"
    exit 2
  fi
  # RandomPress must exist (the registry's negative control).
  UV_NO_SYNC=1 uv run python - <<'PY' >> "$LOG" 2>&1
import sys
try:
    from kvpress import RandomPress  # noqa: F401
except ImportError as e:
    print(f"FATAL: RandomPress missing: {e}")
    sys.exit(2)
print("RandomPress available")
PY
  rc=$?
  if [ "$rc" = "2" ]; then
    say "RANDOMPRESS_UNAVAILABLE — aborting"
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
run_pool_check() {
  say "=== pool_check (W4 scoping; zero generations)"
  UV_NO_SYNC=1 uv run python - <<'PY' 2>&1 | tee -a "$LOG"
from datasets import load_dataset
ds = load_dataset("google-research-datasets/tydiqa", "secondary_task")
for name, code in (("bengali", "bn"), ("telugu", "te")):
    val = [r for r in ds["validation"] if r["id"].startswith(f"{name}-")]
    print(f"{code}: TyDiQA-GoldP validation pool = {len(val)} items "
          f"(current eval uses [:100]; extension headroom = {len(val)-100})")
PY
  say POOL_CHECK_DONE
}

# ---------------------------------------------------------------------------
run_main() {
  say "=== main start (constant w=256 at r=0.75 + random-eviction control)"
  run_mlkv --model "$QWEN" --task mrag --langs en,bn,te --ctx 8k \
    --configs "baseline,snapkv@r0.75:w256,random@r0.75" \
    --max-items "$N" --max-new-tokens "$CAP" \
    --db results/constant.db
  snap constant
  say ALL_ICLR6_MAIN_DONE
}

preflight

case "$BLOCK" in
  pool_check) run_pool_check ;;
  main) run_main ;;
  chain) run_pool_check; run_main; say ALL_ICLR6_CHAIN_DONE ;;
  *) say "unknown block: $BLOCK"; exit 1 ;;
esac
