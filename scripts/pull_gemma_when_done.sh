#!/bin/bash
# Local overnight puller. Poll the Gemma pod until ALL_ICLR_GEMMA_DONE
# (or 1800 R2-ready rows), scp dbs to this Mac, verify, touch SYNCED.
# Run under caffeinate so the laptop does not idle-sleep.
set -u
POD=r948gmdyb92lxo
DEST="${DEST:-$HOME/working_space/research/mlkv/results}"
LOG="${LOG:-$HOME/working_space/research/mlkv/results/pull_gemma.log}"
AUTH="Authorization: Bearer $(cat "$HOME/.config/runpod/api_key")"
mkdir -p "$DEST"
say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }

ssh_opts="-n -o StrictHostKeyChecking=accept-new -o ConnectTimeout=12 -o BatchMode=yes"

conn() {
  curl -s --max-time 15 -H "$AUTH" "https://rest.runpod.io/v1/pods/$POD" \
    | python3 -c "
import json,sys
p=json.load(sys.stdin)
ip=p.get('publicIp') or ''
pm=p.get('portMappings') or {}
port=pm.get('22') or ''
st=p.get('desiredStatus','')
print(st, ip, port)
"
}

ready_on_pod() {
  local ip=$1 port=$2
  ssh $ssh_opts -p "$port" root@"$ip" '
    if grep -q ALL_ICLR_GEMMA_DONE /workspace/iclr_gemma.log 2>/dev/null; then echo DONE; exit 0; fi
    python3 -c "
import sqlite3,os
p=\"/workspace/mlkv/results/cliff_gemma.db\"
n=sqlite3.connect(p).execute(\"select count(*) from generations\").fetchone()[0] if os.path.exists(p) else 0
print(n)
"
  ' 2>/dev/null
}

say "ARMED dest=$DEST"
while true; do
  read -r ST IP PORT < <(conn)
  say "pod $ST ip=$IP port=$PORT"
  if [ "$ST" = "EXITED" ] || [ "$ST" = "EXITED " ]; then
    say "pod EXITED before pull — volume still has the db; start the pod to scp"
    exit 2
  fi
  if [ -n "$IP" ] && [ -n "$PORT" ]; then
    info=$(ready_on_pod "$IP" "$PORT" || echo FAIL)
    say "remote: $info"
    if echo "$info" | grep -q DONE || echo "$info" | grep -qx 1800; then
      break
    fi
  fi
  sleep 180
done

say "pulling"
mkdir -p "$DEST"
for f in cliff_gemma.db cliff_gemma-snapshot.db cliff_gemma-final.db; do
  scp -P "$PORT" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30 \
    root@"$IP":/workspace/mlkv/results/$f "$DEST/" 2>>"$LOG" || true
done
# verify the live db at least
python3 - "$DEST/cliff_gemma.db" <<'PY' | tee -a "$LOG"
import sqlite3, sys
p = sys.argv[1]
c = sqlite3.connect(p)
assert c.execute("PRAGMA quick_check").fetchone()[0] == "ok"
n = c.execute("select count(*) from generations").fetchone()[0]
print("verified", p, "n=", n)
if n < 1800:
    raise SystemExit(f"too few rows: {n}")
print(c.execute("select lang, config, count(*) from generations group by 1,2").fetchall())
PY
rc=$?
if [ "$rc" != "0" ]; then
  say "VERIFY FAILED rc=$rc — not touching SYNCED"
  exit 1
fi
ssh $ssh_opts -p "$PORT" root@"$IP" 'touch /workspace/SYNCED && echo SYNCED'
say "PULL_OK SYNCED — self_stop may now stop the pod"
exit 0
