#!/bin/bash
# Day-3 chain, pod A: decode-cap fixes and press generality (F3 deferred).
# Specs and registered predictions: docs/day3-runbook.md §1.
# Launch:  setsid bash /workspace/mlkv/scripts/e_day3a.sh &
# Re-arm self-stop with marker ALL_DAY3A_DONE before launching.
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH
cd /workspace/mlkv
LOG=/workspace/day3a.log
M=Qwen/Qwen3-4B

say() { echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }

say "=== day3a chain start"
say "HEAD $(git rev-parse --short HEAD)"

if ! uv run pytest -q tests/test_compression.py tests/test_mrag.py tests/test_mrag_bp.py 2>&1 | tail -1 >> "$LOG"; then
  say "TESTS_FAILED — aborting chain"
  exit 1
fi
say TESTS_OK

# F1a: E3 decisive cells rerun at cap 384 — separates real damage from
# truncation (pivot doc §9). Fresh db: run_keys do not include the cap.
uv run mlkv run --model $M --task mrag-bp --langs el,hi,ru --byte-ctx 12k \
  --configs baseline,snapkv@b2048,snapkv@bb8192,snapkv@r0.6 \
  --max-items 100 --max-new-tokens 384 --db results/e3_384.db 2>&1 | tail -1 >> "$LOG"
say F1A_DONE

# F1b: bn/sw Main-A cells remeasured at cap 384 (bn was 30-47% truncated).
uv run mlkv run --model $M --task mrag --langs bn,sw --ctx 8k,16k \
  --configs baseline,snapkv@r0.75,snapkv@b512 \
  --max-items 100 --max-new-tokens 384 --db results/mrag384.db 2>&1 | tail -1 >> "$LOG"
say F1B_DONE

# F1c: the missing instr-first baseline (E1 gap). Cap 128 to match e1.db;
# appending is safe — config "baseline" has no rows there yet.
uv run mlkv run --model $M --task mrag --langs en,th,bn --ctx 8k,16k \
  --configs baseline --mrag-layout instr-first \
  --max-items 100 --max-new-tokens 128 --db results/e1.db 2>&1 | tail -1 >> "$LOG"
say F1C_DONE

# F2: press generality with a-priori dissociation (runbook §1 F2).
# knorm/random are the constant-free negative controls — the sweep's most
# important row. h2o skipped: eager attention, O(n^2) memory at 8k.
# 2-item smoke first per press; a press that cannot even smoke is skipped,
# never allowed to kill the chain.
run_press() {
  local press=$1
  if ! uv run mlkv run --model $M --task mrag --langs en --ctx 8k \
      --configs "${press}@r0.75" --max-items 2 --max-new-tokens 128 \
      --db results/pressgen.db >> "$LOG" 2>&1; then
    say "PRESS_${press}_FAILED — skipping full run"
    return 0
  fi
  uv run mlkv run --model $M --task mrag --langs en,th,bn --ctx 8k \
    --configs "${press}@r0.75,${press}@r0.9375" \
    --max-items 100 --max-new-tokens 128 --db results/pressgen.db 2>&1 | tail -1 >> "$LOG"
  say "PRESS_${press}_DONE"
}
for press in streamingllm tova expected knorm random; do
  run_press "$press"
done
say F2_DONE

# F3 (adaptive window remedy) is DEFERRED — see docs/day3-runbook.md.
# Two reasons: the mechanism is not yet identified (G2 decides), and the
# original window constants came from stale instruction lengths (bn is 73
# Qwen tokens, not 102; adaptive w should be 83/97/98/137, not 84/104/106/166).

# Redundant snapshot (self_stop.sh makes the authoritative -final ones).
# VACUUM INTO refuses to overwrite, so clear the target first.
for db in e1 e3_384 mrag384 pressgen; do
  rm -f "results/$db-snapshot.db"
  python3 -c "
import sqlite3
c = sqlite3.connect('results/$db.db')
c.execute(\"VACUUM INTO 'results/$db-snapshot.db'\")
print('$db', c.execute('SELECT COUNT(*) FROM generations').fetchone()[0], 'rows')
" >> "$LOG" 2>&1
done
say ALL_DAY3A_DONE
