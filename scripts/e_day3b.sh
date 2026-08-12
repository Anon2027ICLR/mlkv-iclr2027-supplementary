#!/bin/bash
# Day-3 chain, pod B: decode-cap dose response, padded instruction,
# task generality (mgsm-stuffed), Telugu densification.
# Specs and registered predictions: docs/day3-runbook.md §2.
# NOTE: pod B ran Main A on Qwen3-14B; this chain uses Qwen3-4B for
# comparability with the mechanism arm — first run downloads ~8 GB once.
# Launch:  setsid bash /workspace/mlkv/scripts/e_day3b.sh &
# Re-arm self-stop with marker ALL_DAY3B_DONE before launching.
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH
cd /workspace/mlkv
LOG=/workspace/day3b.log
M=Qwen/Qwen3-4B

say() { echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }

say "=== day3b chain start"
say "HEAD $(git rev-parse --short HEAD)"

if ! uv run pytest -q tests/test_mrag.py tests/test_mgsm_stuffed.py 2>&1 | tail -1 >> "$LOG"; then
  say "TESTS_FAILED — aborting chain"
  exit 1
fi
say TESTS_OK

# G1: decode-cap sweep — instance 3 measured as a dose-response curve.
# One db PER CAP (run_keys do not include the cap; sharing a db would make
# resume silently skip). Cap-128 points already exist in maina-a.db.
uv run mlkv run --model $M --task mrag --langs en,th,bn --ctx 8k,16k \
  --configs baseline,snapkv@r0.75 \
  --max-items 100 --max-new-tokens 256 --db results/e7_c256.db 2>&1 | tail -1 >> "$LOG"
say G1_C256_DONE
uv run mlkv run --model $M --task mrag --langs en,th,bn --ctx 8k,16k \
  --configs baseline,snapkv@r0.75 \
  --max-items 100 --max-new-tokens 512 --db results/e7_c512.db 2>&1 | tail -1 >> "$LOG"
say G1_DONE

# G2: padded-instruction dose response in ENGLISH — same language, same
# items, only the instruction's token length moves across the 64-token
# window. Distinct item ids (mragPAD<N>-) make one shared db safe.
for pad in 64 96 128; do
  uv run mlkv run --model $M --task mrag --langs en --ctx 8k \
    --configs baseline,snapkv@r0.75 --mrag-instr-pad $pad \
    --max-items 100 --max-new-tokens 128 --db results/pad.db 2>&1 | tail -1 >> "$LOG"
done
# Cliff-moves-with-the-constant cell: pad 96 must break at w64, heal at w128.
uv run mlkv run --model $M --task mrag --langs en --ctx 8k \
  --configs snapkv@r0.75:w128 --mrag-instr-pad 96 \
  --max-items 100 --max-new-tokens 128 --db results/pad.db 2>&1 | tail -1 >> "$LOG"
say G2_DONE

# G3: task generality — MGSM problem buried before the instruction tail,
# numeric EM metric. Cap 768 for CoT (matches the MGSM quant arm).
uv run mlkv run --model $M --task mgsm-stuffed --langs en,th,bn --ctx 8k \
  --configs baseline,snapkv@r0.75,snapkv@r0.75:w256 \
  --max-items 100 --max-new-tokens 768 --db results/stuffed.db 2>&1 | tail -1 >> "$LOG"
say G3_DONE

# G4: Telugu — bn-class fertility, but its instruction (40 tokens) FITS the
# window. Prediction: capacity-language behaviour, not bn behaviour.
uv run mlkv run --model $M --task mrag --langs te --ctx 8k,16k \
  --configs baseline,snapkv@r0.75,snapkv@b512 \
  --max-items 100 --max-new-tokens 384 --db results/mrag384_te.db 2>&1 | tail -1 >> "$LOG"
say G4_DONE

# Redundant snapshot (self_stop.sh makes the authoritative -final ones).
# VACUUM INTO refuses to overwrite, so clear the target first.
for db in e7_c256 e7_c512 pad stuffed mrag384_te; do
  rm -f "results/$db-snapshot.db"
  python3 -c "
import sqlite3
c = sqlite3.connect('results/$db.db')
c.execute(\"VACUUM INTO 'results/$db-snapshot.db'\")
print('$db', c.execute('SELECT COUNT(*) FROM generations').fetchone()[0], 'rows')
" >> "$LOG" 2>&1
done
say ALL_DAY3B_DONE
