#!/bin/bash
# Local puller for the 8B slice. Same shape as pull_gemma_when_done.sh.
set -u
POD=r948gmdyb92lxo
DEST="${DEST:-$HOME/working_space/research/mlkv/results}"
LOG="${LOG:-$HOME/working_space/research/mlkv/results/pull_8b.log}"
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
print(p.get('desiredStatus',''), ip, pm.get('22') or '')
"
}

say "ARMED dest=$DEST"
while true; do
  read -r ST IP PORT < <(conn)
  say "pod $ST ip=$IP port=$PORT"
  if [ "$ST" = "EXITED" ]; then
    say "pod EXITED before pull — start it to scp"
    exit 2
  fi
  if [ -n "$IP" ] && [ -n "$PORT" ]; then
    info=$(ssh $ssh_opts -p "$PORT" root@"$IP" '
      if grep -q ALL_ICLR_AW_8B_V2_DONE /workspace/iclr_aw_8b_v2.log 2>/dev/null; then echo DONE; exit 0; fi
      python3 -c "import sqlite3,os
p=\"/workspace/mlkv/results/autowin_8b.db\"
print(sqlite3.connect(p).execute(\"select count(*) from generations\").fetchone()[0] if os.path.exists(p) else 0)"
    ' 2>/dev/null || echo FAIL)
    say "remote: $info"
    if echo "$info" | grep -q DONE || echo "$info" | grep -qx 600; then
      break
    fi
  fi
  sleep 180
done

say "pulling"
for f in autowin_8b.db autowin_8b-snapshot.db autowin_8b-final.db; do
  scp -P "$PORT" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30 \
    root@"$IP":/workspace/mlkv/results/$f "$DEST/" 2>>"$LOG" || true
done
if ! python3 - "$DEST/autowin_8b.db" <<'PY' >>"$LOG" 2>&1
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
assert c.execute("PRAGMA quick_check").fetchone()[0] == "ok"
n = c.execute("select count(*) from generations").fetchone()[0]
print("verified n=", n)
print(c.execute("select lang, config, count(*) from generations group by 1,2").fetchall())
if n < 600:
    raise SystemExit("too few rows")
PY
then
  say "VERIFY FAILED"
  exit 1
fi
ssh $ssh_opts -p "$PORT" root@"$IP" 'touch /workspace/SYNCED && echo SYNCED'
say "PULL_OK SYNCED"
exit 0
