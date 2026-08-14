#!/bin/bash
# ICLR remaining arms. Specs: docs/iclr-preregister-2026-08-14.md
#
# Usage:
#   e_iclr.sh chain_a     # cliff_en then schema   -> migration
#   e_iclr.sh chain_b     # cliff_multi then autowin -> mlkv-b
#   e_iclr.sh chain_c     # gemma                  -> mlkv-c2
#   e_iclr.sh cliff_en|cliff_multi|autowin|gemma|schema   # single block
#
# UV_NO_SYNC is not optional. C2 is pinned to torch 2.11.0+cu128 because its
# host driver is CUDA 12.8; an implicit uv sync reinstalls the lockfile's
# cu130 wheel and breaks model load. Harmless on A/B (13.x driver). See
# docs/runpod-api-guide.md §7.
set -u
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1
cd /workspace/mlkv
BLOCK=${1:?usage: e_iclr.sh chain_a|chain_b|chain_c|cliff_en|cliff_multi|autowin|gemma|schema}
LOG=/workspace/iclr_${BLOCK}.log
QWEN=Qwen/Qwen3-4B
GEMMA=google/gemma-3-4b-it
CAP=384
N=100

say() { echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }

preflight() {
  say "=== preflight HEAD $(git rev-parse --short HEAD) UV_NO_SYNC=${UV_NO_SYNC:-unset}"
  if command -v nvidia-smi >/dev/null; then
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader >> "$LOG" 2>&1 || true
    nvidia-smi | sed -n 's/.*CUDA Version: \([0-9.]*\).*/host_cuda \1/p' | head -1 >> "$LOG" || true
  fi
  UV_NO_SYNC=1 python3 - <<'PY' >> "$LOG" 2>&1
import torch
print("torch", torch.__version__, "torch_cuda", torch.version.cuda,
      "cuda_available", torch.cuda.is_available())
PY
  # Abort if the wheel needs a newer CUDA than the host advertises.
  UV_NO_SYNC=1 python3 - <<'PY' >> "$LOG" 2>&1
import re, subprocess, sys, torch
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

aw() {
  # AutoWindow w for one language from measure_c.py (tokenizer, not a table).
  local model=$1 lang=$2
  UV_NO_SYNC=1 python3 scripts/measure_c.py --models "$model" --langs "$lang" \
    | awk -v L="$lang" '$2==L {print $6; exit}'
}

run_cliff_en() {
  say "=== cliff_en start"
  for pad in 48 64 96 128; do
    UV_NO_SYNC=1 uv run mlkv run --model $QWEN --task mrag --langs en --ctx 8k \
      --configs snapkv@r0.75:w32,snapkv@r0.75:w56,snapkv@r0.75:w80,snapkv@r0.75:w104,snapkv@r0.75:w144 \
      --mrag-instr-pad $pad --max-items $N --max-new-tokens $CAP \
      --db results/cliff_en.db 2>&1 | tail -1 >> "$LOG"
    say "CLIFF_EN_PAD${pad}_DONE"
  done
  snap cliff_en
  say ALL_ICLR_CLIFF_EN_DONE
}

run_cliff_multi() {
  say "=== cliff_multi start"
  UV_NO_SYNC=1 uv run mlkv run --model $QWEN --task mrag \
    --langs en,th,sw,bn,te --ctx 8k \
    --configs baseline,snapkv@r0.75:w32,snapkv@r0.75:w56,snapkv@r0.75:w88,snapkv@r0.75:w120,snapkv@r0.75:w176 \
    --max-items $N --max-new-tokens $CAP \
    --db results/cliff_multi.db 2>&1 | tail -1 >> "$LOG"
  snap cliff_multi
  say ALL_ICLR_CLIFF_MULTI_DONE
}

run_autowin() {
  say "=== autowin start (c from tokenizer)"
  UV_NO_SYNC=1 python3 scripts/measure_c.py --models $QWEN \
    --langs en,zh,es,vi,th,sw,bn,te >> "$LOG"
  for lang in en zh es vi th sw bn te; do
    w=$(aw $QWEN $lang)
    [ -n "$w" ] || { say "FATAL: no autowin w for $lang"; exit 1; }
    say "autowin $lang w=$w"
    UV_NO_SYNC=1 uv run mlkv run --model $QWEN --task mrag --langs $lang --ctx 8k \
      --configs baseline,snapkv@r0.75,snapkv@r0.75:w${w} \
      --max-items $N --max-new-tokens $CAP \
      --db results/autowin.db 2>&1 | tail -1 >> "$LOG"
    say "AUTOWIN_${lang}_DONE"
  done
  snap autowin
  say ALL_ICLR_AUTOWIN_DONE
}

run_gemma() {
  say "=== gemma start"
  UV_NO_SYNC=1 python3 scripts/measure_c.py --models $GEMMA --langs en,bn,te >> "$LOG"
  UV_NO_SYNC=1 uv run mlkv run --model $GEMMA --task mrag --langs en,bn,te --ctx 8k \
    --configs baseline,snapkv@r0.75:w16,snapkv@r0.75:w24,snapkv@r0.75:w32,snapkv@r0.75:w48,snapkv@r0.75:w64 \
    --max-items $N --max-new-tokens $CAP \
    --db results/cliff_gemma.db 2>&1 | tail -1 >> "$LOG"
  snap cliff_gemma
  say ALL_ICLR_GEMMA_DONE
}

run_schema() {
  say "=== schema start"
  w=$(aw $QWEN en)
  [ -n "$w" ] || { say "FATAL: no autowin w for en"; exit 1; }
  say "schema AutoWindow w=$w"
  for pad in 60 120 200; do
    UV_NO_SYNC=1 uv run mlkv run --model $QWEN --task mrag --langs en --ctx 8k \
      --configs baseline,snapkv@r0.75,snapkv@r0.75:w${w} \
      --mrag-instr-pad $pad --mrag-tail json \
      --max-items $N --max-new-tokens $CAP \
      --db results/schema.db 2>&1 | tail -1 >> "$LOG"
    say "SCHEMA_PAD${pad}_DONE"
  done
  snap schema
  say ALL_ICLR_SCHEMA_DONE
}

preflight

case "$BLOCK" in
  cliff_en) run_cliff_en ;;
  cliff_multi) run_cliff_multi ;;
  autowin) run_autowin ;;
  gemma) run_gemma ;;
  schema) run_schema ;;
  chain_a) run_cliff_en; run_schema; say ALL_ICLR_A_DONE ;;
  chain_b) run_cliff_multi; run_autowin; say ALL_ICLR_B_DONE ;;
  chain_c) run_gemma; say ALL_ICLR_C_DONE ;;
  *) say "unknown block: $BLOCK"; exit 1 ;;
esac
