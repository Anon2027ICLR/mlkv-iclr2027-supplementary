#!/bin/bash
# On-pod sequencer for docs/review-response-plan-2026-08-17.md §2–3.
# chain (llama + instr_first), then optional llama_te and instr_first_th
# if the required chain finished cleanly.
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
LOG=/workspace/iclr3_all.log
say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }

say "=== wrapper start HEAD=$(git rev-parse --short HEAD 2>/dev/null || echo nogit) UV_NO_SYNC=$UV_NO_SYNC ==="
bash scripts/e_iclr3.sh chain
if grep -q ALL_ICLR3_CHAIN_DONE /workspace/iclr3_chain.log 2>/dev/null; then
  say "chain ok — optional llama_te"
  bash scripts/e_iclr3.sh llama_te || say "llama_te failed, continuing"
  say "optional instr_first_th"
  bash scripts/e_iclr3.sh instr_first_th || say "instr_first_th failed, continuing"
else
  say "chain missing DONE — skip optional blocks"
fi
say ALL_ICLR3_ALL_DONE
