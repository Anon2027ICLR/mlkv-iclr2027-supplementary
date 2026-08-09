#!/bin/bash
export HF_HOME=/workspace/hf
export PATH=$HOME/.local/bin:$PATH
cd /workspace/mlkv
LOG=results/pilot.log

# Arm 1 — MGSM x quantization family (prereg core; Gate-1 backbone)
for MODEL in Qwen/Qwen3-4B meta-llama/Llama-3.1-8B-Instruct; do
  uv run mlkv run --model "$MODEL" --task mgsm --langs en,vi,zh,sw \
    --configs baseline,kv4,kv2 --max-new-tokens 768 \
    --db results/pilot.db 2>&1 | tee -a $LOG
done
echo ARM1_MGSM_DONE >> $LOG

# Arm 2 — mRAG x eviction family (amendment: ratio control + budget carries P2)
for MODEL in Qwen/Qwen3-4B meta-llama/Llama-3.1-8B-Instruct; do
  uv run mlkv run --model "$MODEL" --task mrag --langs en,vi,zh,sw --ctx 8k \
    --configs baseline,snapkv@r0.75,snapkv@b1024,snapkv@b2048 \
    --max-items 50 --max-new-tokens 128 \
    --db results/pilot.db 2>&1 | tee -a $LOG
done
echo ARM2_MRAG_DONE >> $LOG

# Arm 3 — NFD 2x2 on Llama-8B vi (NFC halves live in Arm 1)
uv run mlkv run --model meta-llama/Llama-3.1-8B-Instruct --task mgsm --langs vi \
  --configs baseline,kv4 --max-new-tokens 768 --nfd \
  --db results/pilot.db 2>&1 | tee -a $LOG
echo ARM3_NFD_DONE >> $LOG

# Arm 4 — contamination canary (baseline only)
for MODEL in Qwen/Qwen3-4B meta-llama/Llama-3.1-8B-Instruct; do
  uv run mlkv run --model "$MODEL" --task mgsm-canary --langs en,vi,zh,sw \
    --configs baseline --max-new-tokens 768 \
    --db results/pilot.db 2>&1 | tee -a $LOG
done
echo ARM4_CANARY_DONE >> $LOG
echo PILOT_ALL_DONE >> $LOG
