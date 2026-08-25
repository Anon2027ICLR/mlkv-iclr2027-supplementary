#!/bin/bash
# Fifth-review Group B arms (2026-08-25). Preregisters (commit before running):
#   docs/iclr-refine-preregister.md   (b1: refine layout, en/bn, n=100)
#   docs/iclr-oracle-preregister.md   (b2: te full pool, w247 + per-item wq)
#   docs/iclr-32b-preregister.md      (b3: Qwen3-32B, bn/te, n=100 -- OWN
#                                      80GB pod; not part of `chain`)
#   docs/iclr-ctx16k-preregister.md   (b4: te at ctx 16k, n=100)
#
# Four self-contained stores; every constant re-derived on-pod with FATAL
# mismatch; the TyDiQA disjointness guard runs keyed to each arm's eval set.
# Chain order (campaign pod): b1 -> b2 -> b4. b3 runs alone on the 80GB pod
# (`e_iclr10.sh b3`), guards included.
#
# Usage:
#   e_iclr10.sh chain          # guards, then b1, b2, b4
#   e_iclr10.sh guards|b1|b2|b3|b4
#
# UV_NO_SYNC is not optional -- docs/runpod-api-guide.md §7.
set -uo pipefail
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1
export HF_HUB_DISABLE_XET=1
cd /workspace/mlkv
BLOCK=${1:?usage: e_iclr10.sh chain|guards|b1|b2|b3|b4}
LOG=/workspace/iclr10_${BLOCK}.log
QWEN=Qwen/Qwen3-4B
QWEN32=Qwen/Qwen3-32B
CAP=384

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
    say "CUDA_MISMATCH -- aborting"
    exit 2
  fi
}

# Shipped integers this chain depends on (Qwen3-4B, locked 2026-08-14 and
# Table `tab:constants`): c en/bn/te = 25/107/167, Q90 bn/te = 76/80.
# b2 uses te's c both as the fixed w247 = 167+80 and as the ":wq167" oracle
# constant; b4 reuses the SAME integers at 16k (their prefill-independence is
# the registered point). b3 (32B) shares the Qwen3 tokenizer, so the shipped
# integers must reproduce there too -- a mismatch means the 32B chat template
# differs, and the registered outcome is the abort.
c_of()   { case "$1" in en) echo 25 ;; bn) echo 107 ;; te) echo 167 ;; esac; }
q90_of() { case "$1" in bn) echo 76 ;; te) echo 80 ;; esac; }

guard_c() {  # guard_c <model> <lang> -> asserts measure_c c == shipped
  local model=$1 lang=$2 c expected
  c=$(UV_NO_SYNC=1 uv run python scripts/measure_c.py --models "$model" \
    --langs "$lang" | tee -a "$LOG" | awk -v L="$lang" '$2==L {print $5; exit}')
  expected=$(c_of "$lang")
  if [ "$c" != "$expected" ]; then
    say "FATAL: on-pod c for $lang ($model) is '$c', shipped is $expected -- drift, do not run"
    exit 1
  fi
  say "guard c[$lang]=$c == shipped ($model)"
}

guard_q90() {  # guard_q90 <lang> -> asserts measure_q Q90 == shipped
  local lang=$1 q expected
  q=$(UV_NO_SYNC=1 uv run python - "$lang" <<'PY'
import json, sys
from pathlib import Path
rows = json.loads(Path("results/q_percentiles.json").read_text())
print(next(int(r["Q90"]) for r in rows if r["lang"] == sys.argv[1]))
PY
)
  expected=$(q90_of "$lang")
  if [ "$q" != "$expected" ]; then
    say "FATAL: on-pod Q90 for $lang is '$q', shipped is $expected -- drift, do not run"
    exit 1
  fi
  say "guard Q90[$lang]=$q == shipped"
}

run_guards() {  # run_guards <model>
  local model=${1:-$QWEN}
  say "=== guards: TyDiQA pools + id disjointness, keyed to each arm's eval set"
  UV_NO_SYNC=1 uv run python - <<'PY' 2>&1 | tee -a "$LOG"
import sys
from datasets import load_dataset
ds = load_dataset("google-research-datasets/tydiqa", "secondary_task")
# Eval slices this chain registers: te full pool (b2), bn val[:100] (b1 and
# b3 run --max-items 100), te-at-16k val[:100] (b4 -- a subset of the full
# pool, so the te full-pool guard covers it).
EXPECT = {"bengali": 113, "telugu": 669}
EVAL_SLICE = {"bengali": 100, "telugu": None}  # None = full pool
KNOWN_RAW_DUPES = {
    "bengali-3322578321529024800-0",
    "bengali-7245461333310589730-8",
    "bengali-7443250538964255015-1",
}
for name, want in EXPECT.items():
    val = [r["id"] for r in ds["validation"] if r["id"].startswith(f"{name}-")]
    tr_ids = {r["id"] for r in ds["train"] if r["id"].startswith(f"{name}-")}
    raw_overlap = set(val) & tr_ids
    print(f"{name}: validation={len(val)} train={len(tr_ids)} "
          f"raw-overlap={len(raw_overlap)}")
    if len(val) != want:
        print(f"FATAL: {name} validation pool is {len(val)}, preregister says {want}")
        sys.exit(2)
    if raw_overlap - KNOWN_RAW_DUPES:
        print(f"FATAL: unexpected raw split overlap beyond the documented "
              f"duplicates: {sorted(raw_overlap - KNOWN_RAW_DUPES)}")
        sys.exit(2)
    q90_source = tr_ids - set(val[:100])
    n = EVAL_SLICE[name]
    eval_ids = set(val) if n is None else set(val[:n])
    scope = "full pool" if n is None else f"val[:{n}]"
    viol = eval_ids & q90_source
    if viol:
        print(f"FATAL: {len(viol)} eval ids inside the Q90 source: "
              f"{sorted(viol)[:5]}")
        sys.exit(2)
    print(f"  eval({scope}) ∩ Q90-source = 0: the held-out discipline holds")
print("guards OK")
PY
  rc=$?
  if [ "$rc" != "0" ]; then
    say "GUARDS_FAILED -- aborting"
    exit 2
  fi
  say "=== guards: re-derive constants on this pod ($model)"
  UV_NO_SYNC=1 uv run python scripts/measure_q.py --models "$model" \
    --langs bn,te | tee -a "$LOG"
  for lang in en bn te; do guard_c "$model" "$lang"; done
  for lang in bn te; do guard_q90 "$lang"; done
  # b1 additionally asserts the refine geometry: the question must open the
  # rendered prompt, or the layout flag is not doing what the prereg says.
  UV_NO_SYNC=1 uv run python - <<'PY' 2>&1 | tee -a "$LOG"
import sys
from mlkv.tasks import mrag
class Tok:
    def encode(self, t, add_special_tokens=False): return t.split()
q = [{"qid": "probe-0", "question": "Where is the probe?",
      "context": "The probe is in the guard.", "answers": ["guard"]}]
d = [f"Distractor passage number {i} with filler words." for i in range(50)]
items = mrag.build("en", Tok(), [512], pool=(q, d), layout="refine",
                   max_items=1)
p = items[0]["prompt"]
if not p.startswith(mrag.REFINE_PREFIX + "Where is the probe?"):
    print("FATAL: refine layout does not open with the query"); sys.exit(2)
if not p.endswith(mrag.REFINE_SUFFIX):
    print("FATAL: refine layout does not end with the T06 suffix"); sys.exit(2)
print("refine geometry probe OK (query-first, T06 suffix last)")
PY
  rc=$?
  if [ "$rc" != "0" ]; then
    say "GUARDS_FAILED -- aborting"
    exit 2
  fi
  # Derived integers this chain uses, printed for the log:
  # b2: te w247 = 167+80, oracle config snapkv@r0.75:wq167;
  # b4: same w247 at ctx 16k (prefill-independent by construction).
  say GUARDS_DONE
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

run_b1() {
  say "=== b1 refine: T06 layout, en/bn x {baseline,w64}, n=100"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs en \
    --ctx 8k --mrag-layout refine \
    --configs "baseline,snapkv@r0.75" \
    --max-items 100 --max-new-tokens "$CAP" \
    --db results/refine.db 2>&1 | tee -a "$LOG"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs bn \
    --ctx 8k --mrag-layout refine \
    --configs "baseline,snapkv@r0.75" \
    --max-items 100 --max-new-tokens "$CAP" \
    --db results/refine.db 2>&1 | tee -a "$LOG"
  snap refine
  say B1_DONE
}

run_b2() {
  say "=== b2 oracle_depth: te full pool 669 x {baseline,w247,wq167}"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs te \
    --ctx 8k \
    --configs "baseline,snapkv@r0.75:w247,snapkv@r0.75:wq167" \
    --max-items 669 --max-new-tokens "$CAP" \
    --db results/oracle_depth.db 2>&1 | tee -a "$LOG"
  snap oracle_depth
  say B2_DONE
}

run_b4() {
  say "=== b4 ctx16k: te at 16k x {baseline,w64,w247}, n=100"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs te \
    --ctx 16k \
    --configs "baseline,snapkv@r0.75,snapkv@r0.75:w247" \
    --max-items 100 --max-new-tokens "$CAP" \
    --db results/ctx16k.db 2>&1 | tee -a "$LOG"
  snap ctx16k
  say B4_DONE
}

run_b3() {
  say "=== b3 qwen32b: bn/te x {baseline,w64,w-hat}, n=100 (own 80GB pod)"
  run_guards "$QWEN32"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN32" --task mrag --langs bn \
    --ctx 8k --configs "baseline,snapkv@r0.75,snapkv@r0.75:w183" \
    --max-items 100 --max-new-tokens "$CAP" \
    --db results/qwen32b.db 2>&1 | tee -a "$LOG"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN32" --task mrag --langs te \
    --ctx 8k --configs "baseline,snapkv@r0.75,snapkv@r0.75:w247" \
    --max-items 100 --max-new-tokens "$CAP" \
    --db results/qwen32b.db 2>&1 | tee -a "$LOG"
  snap qwen32b
  say B3_DONE
}

preflight

case "$BLOCK" in
  guards) run_guards "$QWEN" ;;
  b1) run_b1 ;;
  b2) run_b2 ;;
  b4) run_b4 ;;
  b3) run_b3 ;;
  chain) run_guards "$QWEN"; run_b1; run_b2; run_b4; say ALL_ICLR10_CHAIN_DONE ;;
  *) say "unknown block: $BLOCK"; exit 1 ;;
esac
