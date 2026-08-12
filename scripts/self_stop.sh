#!/bin/bash
# On-pod self-stop: when this pod's work is finished, snapshot its results,
# prove the snapshot is readable, and only then stop the pod through the RunPod
# API. Independent of the operator's machine and of any supervising session —
# if the laptop sleeps, the pod still stops paying for itself.
#
# Usage: self_stop.sh <pod_id> <marker> <marker_file> <db1[,db2,...]>
#
# Guarantees, in order of importance:
#   - never TERMINATE, only stop: the volume (results, models, venv) survives
#   - never stop on an unverified snapshot; a failed check keeps the pod alive
#     and loud, because a running pod costs dollars and lost results cost days
#   - snapshot via VACUUM INTO, never a copy of a live SQLite file
set -u

POD_ID=$1; MARKER=$2; MARKER_FILE=$3; DBS=$4
LOG=/workspace/self_stop.log
KEY_FILE=/root/.runpod_key
POLL=120
GRACE=120        # let the driver's final writes land before snapshotting
MIN_ROWS=${MIN_ROWS:-1000}  # override per chain: some day-3 dbs are legitimately 600-900 rows
SYNC_WAIT=4500   # hold the pod up to 75 min so the operator can pull results
SYNCED=/workspace/SYNCED   # the operator touches this after a verified pull

say() { echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }

say "=== self-stop armed: pod=$POD_ID marker=$MARKER file=$MARKER_FILE dbs=$DBS"

while true; do
  if grep -q "$MARKER" "$MARKER_FILE" 2>/dev/null; then
    say "marker seen; waiting ${GRACE}s for final writes"
    sleep $GRACE
    break
  fi
  sleep $POLL
done

cd /workspace/mlkv || { say "FATAL: no /workspace/mlkv"; exit 1; }

ok=1
IFS=',' read -ra LIST <<< "$DBS"
for db in "${LIST[@]}"; do
  src="results/$db.db"
  snap="results/$db-final.db"
  if [ ! -f "$src" ]; then
    say "MISSING $src — refusing to stop"; ok=0; continue
  fi
  rm -f "$snap.part"
  rows=$(python3 - "$src" "$snap" <<'PY' 2>>"$LOG"
import sqlite3, sys, os
src, snap = sys.argv[1], sys.argv[2]
db = sqlite3.connect(src, timeout=120)
db.execute(f"VACUUM INTO '{snap}.part'")
db.close()
c = sqlite3.connect(f"{snap}.part")
assert c.execute("PRAGMA quick_check").fetchone()[0] == "ok"
n = c.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
c.close()
os.replace(f"{snap}.part", snap)
print(n)
PY
)
  if [ -z "$rows" ] || [ "$rows" -lt "$MIN_ROWS" ] 2>/dev/null; then
    say "VERIFY FAILED for $db (rows=${rows:-none}) — refusing to stop"; ok=0
  else
    say "verified $db: $rows rows -> $snap"
  fi
done

if [ "$ok" != "1" ]; then
  say "NOT STOPPING — snapshots unverified; pod stays up for a human"
  exit 1
fi

# The pod cannot push results to the operator's laptop, so hold it alive long
# enough to be pulled. Stop early the moment a verified pull reports in; cap the
# wait so a dead session cannot leave the GPU billing overnight.
rm -f "$SYNCED"
say "results ready; waiting up to $((SYNC_WAIT / 60)) min for a pull (touch $SYNCED to release)"
waited=0
while [ $waited -lt $SYNC_WAIT ]; do
  if [ -f "$SYNCED" ]; then
    say "pull confirmed after ${waited}s — stopping now"
    break
  fi
  sleep 60
  waited=$((waited + 60))
done
[ -f "$SYNCED" ] || say "no pull within $((SYNC_WAIT / 60)) min — stopping anyway, results are on the volume"

code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 -X POST \
  -H "Authorization: Bearer $(cat "$KEY_FILE")" \
  "https://rest.runpod.io/v1/pods/$POD_ID/stop" 2>/dev/null)
say "stop request -> HTTP $code"
case "$code" in
  200|201|202|204) say "STOPPED_OK"; exit 0 ;;
esac

# REST refused: try GraphQL once before giving up, then keep the pod alive and
# say so — silently failing here is what burns a night of GPU time.
gql=$(curl -s --max-time 30 -X POST \
  -H "Authorization: Bearer $(cat "$KEY_FILE")" -H "Content-Type: application/json" \
  -d "{\"query\":\"mutation { podStop(input: {podId: \\\"$POD_ID\\\"}) { id desiredStatus } }\"}" \
  "https://api.runpod.io/graphql" 2>/dev/null)
case "$gql" in
  *desiredStatus*|*EXITED*) say "STOPPED_OK via GraphQL"; exit 0 ;;
esac
say "STOP FAILED (REST $code; GraphQL: ${gql:0:120}) — pod still running, needs a human"
exit 1
