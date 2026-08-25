#!/bin/bash
# On-pod sequencer for docs/second-review-response-plan-2026-08-17.md §B.
# chain = bn_ladder + agnostic + ratio; optional tova if chain is clean.
set -u
export HF_HOME=/workspace/hf
export PATH=$HOME/.local/bin:$PATH
export UV_NO_SYNC=1
export HF_HUB_DISABLE_XET=1
if [ -f /root/.cache/huggingface/token ]; then
  export HF_TOKEN=$(cat /root/.cache/huggingface/token)
  export HUGGING_FACE_HUB_TOKEN=$HF_TOKEN
fi
cd /workspace/mlkv
LOG=/workspace/iclr4_all.log
say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }

# measure_q in the ratio block overwrites results/q_percentiles.json
if [ -f results/q_percentiles.json ]; then
  cp -a results/q_percentiles.json /workspace/q_percentiles.json.LOCKED
fi

say "=== wrapper start HEAD=$(git rev-parse --short HEAD 2>/dev/null || echo nogit) ==="
bash scripts/e_iclr4.sh chain
if [ -f /workspace/q_percentiles.json.LOCKED ]; then
  cp -a /workspace/q_percentiles.json.LOCKED results/q_percentiles.json
fi
if grep -q ALL_ICLR4_CHAIN_DONE /workspace/iclr4_chain.log 2>/dev/null; then
  say "chain ok — optional agnostic_tova"
  bash scripts/e_iclr4.sh agnostic_tova || say "agnostic_tova failed, continuing"
else
  say "chain missing DONE — skip tova"
fi
if [ -f /workspace/q_percentiles.json.LOCKED ]; then
  cp -a /workspace/q_percentiles.json.LOCKED results/q_percentiles.json
fi
say ALL_ICLR4_ALL_DONE
