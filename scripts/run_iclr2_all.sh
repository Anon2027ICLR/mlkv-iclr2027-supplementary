#!/bin/bash
# On-pod sequencer for docs/iclr-followup-plan-2026-08-17.md §2.
# Does not edit preregistered predictions or windows.
set -u
export HF_HOME=/workspace/hf
export PATH=$HOME/.local/bin:$PATH
export UV_NO_SYNC=1
if [ -f /root/.cache/huggingface/token ]; then
  export HF_TOKEN=$(cat /root/.cache/huggingface/token)
  export HUGGING_FACE_HUB_TOKEN=$HF_TOKEN
fi
cd /workspace/mlkv
LOG=/workspace/iclr2_all.log
say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }

say "=== wrapper start HEAD=$(git rev-parse --short HEAD 2>/dev/null || echo nogit) UV_NO_SYNC=$UV_NO_SYNC ==="
if [ -f /workspace/q_percentiles.json.LOCKED ]; then
  cp -a /workspace/q_percentiles.json.LOCKED results/q_percentiles.json
fi

bash scripts/e_iclr2.sh chain_qwen
if [ -f /workspace/q_percentiles.json.LOCKED ]; then
  cp -a /workspace/q_percentiles.json.LOCKED results/q_percentiles.json
fi

if grep -q ALL_ICLR2_QWEN_DONE /workspace/iclr2_chain_qwen.log 2>/dev/null; then
  say "qwen chain ok — optional v_trace_bn"
  bash scripts/e_iclr2.sh v_trace_bn || say "v_trace_bn failed, continuing"
else
  say "qwen chain missing DONE marker — skip v_trace_bn, still try gemma"
fi

bash scripts/e_iclr2.sh gemma_q90
if [ -f /workspace/q_percentiles.json.LOCKED ]; then
  cp -a /workspace/q_percentiles.json.LOCKED results/q_percentiles.json
fi
say ALL_ICLR2_ALL_DONE
