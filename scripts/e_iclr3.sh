#!/bin/bash
# Review-response arms (2026-08-17). Preregisters:
#   llama       -> docs/iclr-llama-preregister.md
#   instr_first -> docs/iclr-instr-first-preregister.md
# Plan: docs/review-response-plan-2026-08-17.md
#
# Usage:
#   e_iclr3.sh chain         # llama then instr_first (one pod)
#   e_iclr3.sh llama|llama_te|instr_first|instr_first_th   # single block
#
# The Llama weights are GATED: the pod's HF token must have
# meta-llama/Llama-3.1-8B-Instruct access, or the llama block dies in
# preflight. All w are measured on-pod; never copied from a doc. A fresh
# pod is a new stack: every block re-runs its own baselines and pairs
# only within its own db.
#
# UV_NO_SYNC is not optional — see docs/runpod-api-guide.md §7.
set -u
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1
export HF_HUB_DISABLE_XET=1
if [ -f /root/.cache/huggingface/token ]; then
  export HF_TOKEN=$(cat /root/.cache/huggingface/token)
  export HUGGING_FACE_HUB_TOKEN=$HF_TOKEN
fi
cd /workspace/mlkv
BLOCK=${1:?usage: e_iclr3.sh chain|llama|llama_te|instr_first|instr_first_th}
LOG=/workspace/iclr3_${BLOCK}.log
QWEN=Qwen/Qwen3-4B
LLAMA=meta-llama/Llama-3.1-8B-Instruct
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

llama_gate() {
  # Fail fast if the token cannot see the gated repo.
  UV_NO_SYNC=1 uv run python - <<'PY'
from huggingface_hub import auth_check
auth_check("meta-llama/Llama-3.1-8B-Instruct")
print("llama access OK")
PY
  [ $? -eq 0 ] || { say "FATAL: no HF access to $LLAMA — fix the pod token"; exit 3; }
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
llama_lang() {
  # $1 = lang. hat_w = c + Q90, both measured on the Llama tokenizer.
  local lang=$1
  local w
  w=$(UV_NO_SYNC=1 uv run python - "$lang" <<'PY'
import json, sys
from pathlib import Path
lang = sys.argv[1]
c = None
for line in Path("/tmp/c_llama.txt").read_text().splitlines():
    p = line.split()
    if len(p) >= 6 and p[1] == lang and p[4].isdigit():
        c = int(p[4])
if c is None:
    raise SystemExit(f"no c for {lang}")
rows = json.loads(Path("results/q_percentiles_llama.json").read_text())
q90 = next(int(r["Q90"]) for r in rows if r["lang"] == lang)
print(c + q90)
PY
)
  [ -n "$w" ] || { say "FATAL: no hat_w for $lang"; exit 1; }
  say "llama $lang hat_w=$w"
  run_mlkv --model "$LLAMA" --task mrag --langs "$lang" --ctx 8k \
    --configs "baseline,snapkv@r0.75,snapkv@r0.75:w${w}" \
    --max-items "$N" --max-new-tokens "$CAP" \
    --db results/llama.db
  say "LLAMA_${lang}_DONE"
}

llama_measure() {
  UV_NO_SYNC=1 uv run python scripts/measure_c.py --models "$LLAMA" \
    --langs en,bn,te | tee /tmp/c_llama.txt | tee -a "$LOG"
  UV_NO_SYNC=1 uv run python scripts/measure_q.py --models "$LLAMA" \
    --langs en,bn,te --out results/q_percentiles_llama.json | tee -a "$LOG"
}

run_llama() {
  say "=== llama start (third tokenizer family; en+bn primary)"
  llama_gate
  llama_measure
  for lang in en bn; do llama_lang "$lang"; done
  snap llama
  say ALL_ICLR3_LLAMA_DONE
}

run_llama_te() {
  say "=== llama_te start (optional)"
  llama_gate
  [ -f /tmp/c_llama.txt ] || llama_measure
  llama_lang te
  snap llama
  say ALL_ICLR3_LLAMA_TE_DONE
}

# ---------------------------------------------------------------------------
run_instr_first() {
  say "=== instr_first start (cap-384 clean head-to-head; V=1 by construction)"
  run_mlkv --model "$QWEN" --task mrag --langs en,bn,te --ctx 8k \
    --mrag-layout instr-first \
    --configs "baseline,snapkv@r0.75" \
    --max-items "$N" --max-new-tokens "$CAP" \
    --db results/instr_first.db
  snap instr_first
  say ALL_ICLR3_INSTR_FIRST_DONE
}

run_instr_first_th() {
  say "=== instr_first_th start (optional; layout-tax check)"
  run_mlkv --model "$QWEN" --task mrag --langs th --ctx 8k \
    --mrag-layout instr-first \
    --configs "baseline,snapkv@r0.75" \
    --max-items "$N" --max-new-tokens "$CAP" \
    --db results/instr_first.db
  snap instr_first
  say ALL_ICLR3_INSTR_FIRST_TH_DONE
}

preflight

case "$BLOCK" in
  llama) run_llama ;;
  llama_te) run_llama_te ;;
  instr_first) run_instr_first ;;
  instr_first_th) run_instr_first_th ;;
  chain) run_llama; run_instr_first; say ALL_ICLR3_CHAIN_DONE ;;
  *) say "unknown block: $BLOCK"; exit 1 ;;
esac
