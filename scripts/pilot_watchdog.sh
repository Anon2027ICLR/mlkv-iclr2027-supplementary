#!/bin/bash
# On-box watchdog for the mlkv pilot: heartbeat + auto-restart, fully
# independent of the operator's machine.
# Heartbeats to /workspace/watchdog.log every 5 min; exits when pilot completes.
DB=/workspace/mlkv/results/pilot.db
PLOG=/workspace/mlkv/results/pilot.log
WLOG=/workspace/watchdog.log
MAX_RESTARTS=5
restarts=0
last_rows=-1
last_change=$(date +%s)

log() { echo "$(date -u +%FT%TZ) $*" >> "$WLOG"; }

rows_now() {
  python3 - <<'PY' 2>/dev/null || echo -1
import sqlite3
try:
    c = sqlite3.connect("/workspace/mlkv/results/pilot.db", timeout=5)
    print(c.execute("SELECT COUNT(*) FROM generations").fetchone()[0])
except Exception:
    print(-1)
PY
}

start_pilot() {
  setsid nohup bash /root/run_pilot_all.sh </dev/null >>/workspace/pilot_nohup.log 2>&1 &
}

log "watchdog started (pid $$)"
while true; do
  if grep -q PILOT_ALL_DONE "$PLOG" 2>/dev/null; then
    log "PILOT_ALL_DONE — watchdog exiting"
    exit 0
  fi
  alive=$(pgrep -fc "bin/mlkv run")
  rows=$(rows_now)
  gpu=$(nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv,noheader 2>/dev/null | tr -d " ")
  oom=$(grep -o "oom_kill [0-9]*" /sys/fs/cgroup/memory.events 2>/dev/null)
  now=$(date +%s)
  if [ "$rows" -gt "$last_rows" ] 2>/dev/null; then last_rows=$rows; last_change=$now; fi
  age=$(( now - last_change ))
  log "hb alive=$alive rows=$rows stall=${age}s gpu=$gpu $oom restarts=$restarts"
  if [ "$alive" -eq 0 ] 2>/dev/null; then
    if [ "$restarts" -lt "$MAX_RESTARTS" ]; then
      restarts=$((restarts+1)); log "PILOT DEAD -> RESTART #$restarts"
      start_pilot; last_change=$now
    else
      log "PILOT DEAD, MAX_RESTARTS reached — heartbeat only, needs human"
    fi
  elif [ "$age" -gt 2700 ]; then
    log "STALL ${age}s with live process -> kill + restart"
    pkill -f "run_pilot_all[.]sh"; pkill -f "bin/mlkv run"; sleep 10
    if [ "$restarts" -lt "$MAX_RESTARTS" ]; then
      restarts=$((restarts+1)); log "RESTART #$restarts after stall"
      start_pilot
    fi
    last_change=$now
  fi
  sleep 300
done
