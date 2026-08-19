#!/bin/bash
# Constant-at-scale arm (2026-08-19). Preregister:
#   docs/iclr-constant-depth-preregister.md   (commit + release push before running)
#
# w=256 against the shipped AutoWindow integers on the ENTIRE TyDiQA-GoldP
# validation pools (te 669, bn 113). Per language the baseline is generated
# FIRST and ALONE, because the pairing license (preregister guard G2) is
# decided on it: if this pod reproduces stack d7368e8bd94a and the fresh
# baselines are byte-identical to results/depth.db, the depth store's
# hat-w cells are pairable (branch A) and only w256 is generated; otherwise
# the shipped hat-w configs are generated here too (branch B) and pairing
# stays inside this store. If depth.db is absent the driver cannot verify
# byte-identity and takes branch B as a conservative superset -- extra
# hat-w rows only add checks, they can never weaken the registration.
#
# Usage:
#   e_iclr8.sh chain     # guards, then te, then bn
#   e_iclr8.sh guards|te|bn
#
# UV_NO_SYNC is not optional -- docs/runpod-api-guide.md §7.
set -uo pipefail
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1
export HF_HUB_DISABLE_XET=1
cd /workspace/mlkv
BLOCK=${1:?usage: e_iclr8.sh chain|guards|te|bn}
LOG=/workspace/iclr8_${BLOCK}.log
QWEN=Qwen/Qwen3-4B
CAP=384
CONST=256
STORE=constant_depth
EXPECTED_STACK=d7368e8bd94a

what_of() {
  case "$1" in
    bn) echo 183 ;;
    te) echo 247 ;;
    *) echo "" ;;
  esac
}

n_of() {
  case "$1" in
    bn) echo 113 ;;
    te) echo 669 ;;
    *) echo "" ;;
  esac
}

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

run_guards() {
  say "=== guards: pool sizes, id disjointness, shipped integers"
  UV_NO_SYNC=1 uv run python - <<'PY' 2>&1 | tee -a "$LOG"
import sys
from datasets import load_dataset
ds = load_dataset("google-research-datasets/tydiqa", "secondary_task")
EXPECT = {"bengali": 113, "telugu": 669}
# Known dataset wart, documented in the depth preregister's amendment: three
# Bengali examples are exact duplicates across the raw HF splits. They sit
# inside validation[:100], which measure_q.py has always excluded from the
# train-derived Q90 source, so the invariant that matters is unaffected.
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
    if len(val) != want:
        print(f"FATAL: {name} validation pool is {len(val)}, preregister says {want}")
        sys.exit(2)
    if raw_overlap - KNOWN_DUPES:
        print(f"FATAL: unexpected raw split overlap beyond the documented "
              f"duplicates: {sorted(raw_overlap - KNOWN_DUPES)}")
        sys.exit(2)
    q90_source = tr_ids - set(val[:100])
    viol = set(val) & q90_source
    if viol:
        print(f"FATAL: {len(viol)} eval ids inside the Q90 source: "
              f"{sorted(viol)[:5]}")
        sys.exit(2)
    print(f"  eval(full pool) ∩ Q90-source = 0: the held-out discipline holds")
print("guards OK: pools match the preregister, the Q90 source is disjoint from eval")
PY
  rc=$?
  if [ "$rc" != "0" ]; then
    say "GUARDS_FAILED -- aborting"
    exit 2
  fi
  UV_NO_SYNC=1 uv run python scripts/measure_q.py --models "$QWEN" \
    --langs bn,te | tee -a "$LOG"
  for lang in bn te; do
    local c w expected
    c=$(UV_NO_SYNC=1 uv run python scripts/measure_c.py --models "$QWEN" \
      --langs "$lang" | tee -a "$LOG" | awk -v L="$lang" '$2==L {print $5; exit}')
    [ -n "$c" ] || { say "FATAL: no c for $lang"; exit 1; }
    w=$(UV_NO_SYNC=1 uv run python - "$lang" "$c" <<'PY'
import json, sys
from pathlib import Path
lang, c = sys.argv[1], int(sys.argv[2])
rows = json.loads(Path("results/q_percentiles.json").read_text())
q90 = next(int(r["Q90"]) for r in rows if r["lang"] == lang)
print(c + q90)
PY
)
    expected=$(what_of "$lang")
    if [ "$w" != "$expected" ]; then
      say "FATAL: on-pod hat_w for $lang is $w, shipped integer is $expected -- drift, do not run"
      exit 1
    fi
    say "guard $lang: c=$c hat_w=$w == shipped $expected (constant under test: w=$CONST)"
  done
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

# Prints exactly one line "BRANCH=A" or "BRANCH=B <reason>". Guard G2.
branch_check() {
  local lang=$1
  python3 - "$lang" <<'PY'
import os, sqlite3, sys
lang = sys.argv[1]
EXPECTED_STACK = "d7368e8bd94a"
con = sqlite3.connect(f"file:results/constant_depth.db?mode=ro", uri=True)
stacks = sorted({r[0] for r in con.execute(
    "SELECT DISTINCT stack_id FROM generations")})
if stacks != [EXPECTED_STACK]:
    print(f"BRANCH=B stack {stacks} != {EXPECTED_STACK}"); sys.exit(0)
if not os.path.exists("results/depth.db"):
    print("BRANCH=B depth.db absent on pod, byte-identity unverifiable"); sys.exit(0)
dep = sqlite3.connect("file:results/depth.db?mode=ro", uri=True)
new = {i: o for i, o in con.execute(
    "SELECT item_id, output FROM generations WHERE lang=? AND config='baseline'",
    (lang,))}
old = {i: o for i, o in dep.execute(
    "SELECT item_id, output FROM generations WHERE lang=? AND config='baseline'",
    (lang,))}
if set(new) != set(old):
    print(f"BRANCH=B baseline item sets differ ({len(new)} vs {len(old)})"); sys.exit(0)
diff = sum(1 for i in new if new[i] != old[i])
if diff:
    print(f"BRANCH=B {diff}/{len(new)} baseline rows differ from depth.db"); sys.exit(0)
print("BRANCH=A")
PY
}

run_lang() {
  local lang=$1 n what branch cfgs
  n=$(n_of "$lang"); what=$(what_of "$lang")
  say "=== $lang baseline first (full pool n=$n) -- the pairing license is decided on it"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs "$lang" \
    --ctx 8k --configs baseline \
    --max-items "$n" --max-new-tokens "$CAP" \
    --db "results/${STORE}.db" 2>&1 | tee -a "$LOG"
  branch=$(branch_check "$lang")
  say "$lang $branch"
  cfgs="snapkv@r0.75:w${CONST}"
  case "$branch" in
    BRANCH=A*) : ;;
    BRANCH=B*) cfgs="${cfgs},snapkv@r0.75:w${what}" ;;
    *) say "FATAL: branch_check returned '$branch'"; exit 2 ;;
  esac
  say "=== $lang treatment configs: $cfgs"
  UV_NO_SYNC=1 uv run mlkv run --model "$QWEN" --task mrag --langs "$lang" \
    --ctx 8k --configs "$cfgs" \
    --max-items "$n" --max-new-tokens "$CAP" \
    --db "results/${STORE}.db" 2>&1 | tee -a "$LOG"
  snap "$STORE"
  say "ICLR8_${lang}_DONE"
}

preflight

case "$BLOCK" in
  guards) run_guards ;;
  te) run_lang te ;;
  bn) run_lang bn ;;
  chain) run_guards; run_lang te; run_lang bn; say ALL_ICLR8_CHAIN_DONE ;;
  *) say "unknown block: $BLOCK"; exit 1 ;;
esac
