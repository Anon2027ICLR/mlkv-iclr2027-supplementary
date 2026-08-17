#!/bin/bash
# After A (cliff_en) and S (schema) finish, rerun AutoWindow (D) on this pod.
# Do not start while another mlkv run is on the GPU. Never terminate the pod.
set -u
export PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1 HF_HOME=/workspace/hf
LOG=/workspace/iclr_d_after_as.log
LOCK=/tmp/iclr_d_after_as.lock
POD=r948gmdyb92lxo
SOLO=/workspace/iclr_solo.log

say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }

exec 9>"$LOCK"
if ! flock -n 9; then
  say "another waiter holds $LOCK — exit"
  exit 0
fi

say "ARMED wait A+S then rerun D  HEAD=$(cd /workspace/mlkv && git rev-parse --short HEAD)"

# Solo writes SOLO_AFTER_SCHEMA then ALL_ICLR_SOLO_DONE. Either is enough.
while true; do
  if grep -qE 'SOLO_AFTER_SCHEMA|ALL_ICLR_SOLO_DONE' "$SOLO" 2>/dev/null; then
    say "solo marker seen"
    break
  fi
  sleep 30
done

# Let schema's last writes land; wait until the GPU job is actually gone.
sleep 20
for i in $(seq 1 120); do
  if pgrep -f '/workspace/mlkv/scripts/e_iclr.sh (cliff_en|schema)' >/dev/null; then
    sleep 15
    continue
  fi
  if pgrep -f '/workspace/mlkv/.venv/bin/mlkv run' >/dev/null; then
    sleep 15
    continue
  fi
  break
done
if pgrep -f '/workspace/mlkv/.venv/bin/mlkv run' >/dev/null; then
  say "FATAL: GPU still busy after wait — not starting D"
  exit 1
fi

if [ -f /workspace/mlkv/results/autowin.db ]; then
  n=$(python3 -c "import sqlite3; print(sqlite3.connect('/workspace/mlkv/results/autowin.db').execute('select count(*) from generations').fetchone()[0])" 2>/dev/null || echo 0)
  if [ "${n:-0}" -ge 2400 ]; then
    say "autowin.db already has $n rows — skip rerun"
  else
    say "autowin.db exists with n=$n — rerun will resume/append by run_key"
  fi
fi

# Smoke: the original D fail was system python missing transformers.
cd /workspace/mlkv || { say "FATAL: no /workspace/mlkv"; exit 1; }
w=$(UV_NO_SYNC=1 uv run python scripts/measure_c.py --models Qwen/Qwen3-4B --langs en \
  | awk '$2=="en" {print $6; exit}')
if [ -z "$w" ]; then
  say "FATAL: measure_c still returns no AutoWindow w for en"
  exit 1
fi
say "measure_c smoke ok  en AutoWindow w=$w"

if [ "${n:-0}" -lt 2400 ]; then
  say "START e_iclr.sh autowin"
  bash /workspace/mlkv/scripts/e_iclr.sh autowin
  rc=$?
  say "SOLO_AFTER_AUTOWIN_RERUN rc=$rc"
  if [ "$rc" != "0" ]; then
    say "FATAL: autowin rerun failed"
    exit "$rc"
  fi
fi

echo ALL_ICLR_D_RERUN_DONE >> /workspace/iclr_d_rerun.log
say ALL_ICLR_D_RERUN_DONE

# Schema is 900 rows; default MIN_ROWS=1000 would refuse a complete S.
# Never terminate — self_stop only stops after verified snapshots.
MIN_ROWS=800 nohup bash /workspace/mlkv/scripts/self_stop.sh \
  "$POD" ALL_ICLR_D_RERUN_DONE /workspace/iclr_d_rerun.log \
  autowin,cliff_multi,cliff_en,schema \
  >> /workspace/self_stop_d.log 2>&1 &
say "self_stop re-armed for D (MIN_ROWS=800)"
exit 0
