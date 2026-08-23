#!/bin/bash
# Fourth-review Group B arms (2026-08-24). Preregisters (commit before running):
#   docs/iclr-slack-depth-preregister.md   (b1: te full pool, w183/w199/w247)
#   docs/iclr-xinstr-preregister.md        (b2: EN instruction x bn/te items)
#   docs/iclr-if-depth-preregister.md      (b4: instr-first te full pool)
#   docs/iclr-thsw-preregister.md          (b3: th at w91, sw at w67)
#
# Four self-contained stores; every window integer re-derived on-pod with
# FATAL mismatch; the TyDiQA held-out/eval disjointness guard from the depth
# arm runs unchanged. Chain order b1 -> b2 -> b4 -> b3 (b1 gates the writing
# plan; the rest are independent).
#
# Usage:
#   e_iclr9.sh chain          # guards, then b1, b2, b4, b3
#   e_iclr9.sh guards|b1|b2|b4|b3
#
# UV_NO_SYNC is not optional -- docs/runpod-api-guide.md §7.
set -uo pipefail
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1
export HF_HUB_DISABLE_XET=1
cd /workspace/mlkv
BLOCK=${1:?usage: e_iclr9.sh chain|guards|b1|b2|b4|b3}
LOG=/workspace/iclr9_${BLOCK}.log
QWEN=Qwen/Qwen3-4B
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
# Table `tab:constants`): c en/th/sw/bn/te = 25/45/47/107/167,
# Q90 th/sw/bn/te = 46/20/76/80.
c_of()   { case "$1" in en) echo 25 ;; th) echo 45 ;; sw) echo 47 ;; bn) echo 107 ;; te) echo 167 ;; esac; }
q90_of() { case "$1" in th) echo 46 ;; sw) echo 20 ;; bn) echo 76 ;; te) echo 80 ;; esac; }

guard_c() {  # guard_c <lang> -> asserts measure_c c == shipped
  local lang=$1 c expected
  c=$(UV_NO_SYNC=1 uv run python scripts/measure_c.py --models "$QWEN" \
    --langs "$lang" | tee -a "$LOG" | awk -v L="$lang" '$2==L {print $5; exit}')
  expected=$(c_of "$lang")
  if [ "$c" != "$expected" ]; then
    say "FATAL: on-pod c for $lang is '$c', shipped is $expected -- drift, do not run"
    exit 1
  fi
  say "guard c[$lang]=$c == shipped"
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

run_guards() {
  say "=== guards: TyDiQA pools + id disjointness (depth-arm guard, sw added)"
  UV_NO_SYNC=1 uv run python - <<'PY' 2>&1 | tee -a "$LOG"
import sys
from datasets import load_dataset
ds = load_dataset("google-research-datasets/tydiqa", "secondary_task")
EXPECT = {"bengali": 113, "telugu": 669, "swahili": None}  # sw size recorded, not gated
KNOWN_DUPES = {
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
    if want is not None and len(val) != want:
        print(f"FATAL: {name} validation pool is {len(val)}, preregister says {want}")
        sys.exit(2)
    if raw_overlap - KNOWN_DUPES:
        print(f"FATAL: unexpected raw split overlap beyond the documented "
              f"duplicates: {sorted(raw_overlap - KNOWN_DUPES)}")
        sys.exit(2)
    # Strongest invariant, covering both the n=100 and the full-pool arms:
    # no validation item at all may sit inside the Q90 estimation set
    # (train minus the ids of validation[:100] -- measure_q.py's split).
    q90_source = tr_ids - set(val[:100])
    viol = set(val) & q90_source
    if viol:
        print(f"FATAL: {len(viol)} eval ids inside the Q90 source: "
              f"{sorted(viol)[:5]}")
        sys.exit(2)
    print("  eval(full pool) ∩ Q90-source = 0: the held-out discipline holds")
print("guards OK")
PY
  rc=$?
  if [ "$rc" != "0" ]; then
    say "GUARDS_FAILED -- aborting"
    exit 2
  fi
  say "=== guards: re-derive constants on this pod"
  UV_NO_SYNC=1 uv run python scripts/measure_q.py --models "$QWEN" \
    --langs th,sw,bn,te | tee -a "$LOG"
  for lang in en th sw bn te; do guard_c "$lang"; done
  for lang in th sw bn te; do guard_q90 "$lang"; done
  # Derived windows this chain uses, printed for the log:
  # b1: te w183=c+16 w199=c+32 w247=c+Q90; b2: w101=25+76 w105=25+80;
  # b3: th w91=45+46, sw w67=47+20.
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
  say "=== b1 slack_depth: te full pool 669 x {baseline,w183,w199,w247}"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs te \
    --ctx 8k \
    --configs "baseline,snapkv@r0.75:w183,snapkv@r0.75:w199,snapkv@r0.75:w247" \
    --max-items 669 --max-new-tokens "$CAP" \
    --db results/slack_depth.db 2>&1 | tee -a "$LOG"
  snap slack_depth
  say B1_DONE
}

run_b2() {
  say "=== b2 xinstr: EN instruction, bn/te items, n=100"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs bn \
    --ctx 8k --mrag-instr-lang en \
    --configs "baseline,snapkv@r0.75,snapkv@r0.75:w101" \
    --max-items 100 --max-new-tokens "$CAP" \
    --db results/xinstr.db 2>&1 | tee -a "$LOG"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs te \
    --ctx 8k --mrag-instr-lang en \
    --configs "baseline,snapkv@r0.75,snapkv@r0.75:w105" \
    --max-items 100 --max-new-tokens "$CAP" \
    --db results/xinstr.db 2>&1 | tee -a "$LOG"
  snap xinstr
  say B2_DONE
}

run_b4() {
  say "=== b4 if_depth: instr-first te full pool 669 x {baseline,w64}"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs te \
    --ctx 8k --mrag-layout instr-first \
    --configs "baseline,snapkv@r0.75" \
    --max-items 669 --max-new-tokens "$CAP" \
    --db results/if_depth.db 2>&1 | tee -a "$LOG"
  snap if_depth
  say B4_DONE
}

run_b3() {
  say "=== b3 thsw: th {baseline,w64,w91}, sw {baseline,w64,w67}, n=100"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs th \
    --ctx 8k --configs "baseline,snapkv@r0.75,snapkv@r0.75:w91" \
    --max-items 100 --max-new-tokens "$CAP" \
    --db results/thsw.db 2>&1 | tee -a "$LOG"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs sw \
    --ctx 8k --configs "baseline,snapkv@r0.75,snapkv@r0.75:w67" \
    --max-items 100 --max-new-tokens "$CAP" \
    --db results/thsw.db 2>&1 | tee -a "$LOG"
  snap thsw
  say B3_DONE
}

preflight

case "$BLOCK" in
  guards) run_guards ;;
  b1) run_b1 ;;
  b2) run_b2 ;;
  b4) run_b4 ;;
  b3) run_b3 ;;
  chain) run_guards; run_b1; run_b2; run_b4; run_b3; say ALL_ICLR9_CHAIN_DONE ;;
  *) say "unknown block: $BLOCK"; exit 1 ;;
esac
