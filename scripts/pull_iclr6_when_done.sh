#!/bin/bash
# Local puller for e_iclr6 (constant w=256 at r=0.75 + random ranking control).
# After a verified pull: touch SYNCED, then POST /pods/$POD/stop (guide §12).
set -u
POD="${POD:-}"
DEST="${DEST:-$HOME/working_space/research/mlkv/results}"
LOG="${LOG:-$HOME/working_space/research/mlkv/results/pull_iclr6.log}"
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

[ -n "$POD" ] || { echo "set POD"; exit 2; }
say "ARMED dest=$DEST pod=$POD"
while true; do
  read -r ST IP PORT < <(conn)
  say "pod $ST ip=$IP port=$PORT"
  if [ "$ST" = "EXITED" ]; then
    say "pod EXITED before pull — start it to scp"
    exit 2
  fi
  if [ -n "$IP" ] && [ -n "$PORT" ]; then
    info=$(ssh $ssh_opts -p "$PORT" root@"$IP" '
      if grep -q ALL_ICLR6_CHAIN_DONE /workspace/iclr6_chain.log 2>/dev/null; then echo DONE; exit 0; fi
      python3 -c "
import sqlite3, os
p=\"/workspace/mlkv/results/constant.db\"
n=sqlite3.connect(p).execute(\"select count(*) from generations\").fetchone()[0] if os.path.exists(p) else 0
print(f\"rows constant={n}\")
"
    ' 2>/dev/null || echo FAIL)
    say "remote: $info"
    if echo "$info" | grep -q DONE; then
      break
    fi
  fi
  sleep 180
done

say "pulling"
for f in constant.db constant-snapshot.db constant-final.db; do
  scp -q -P "$PORT" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30 \
    root@"$IP":/workspace/mlkv/results/$f "$DEST/${f}.part" 2>>"$LOG" || true
  if [ -f "$DEST/${f}.part" ]; then
    mv "$DEST/${f}.part" "$DEST/$f"
  fi
done

if ! python3 - "$DEST" <<'PY' >>"$LOG" 2>&1
import sqlite3, sys, os
dest = sys.argv[1]
p = os.path.join(dest, "constant.db")
c = sqlite3.connect(p)
assert c.execute("PRAGMA quick_check").fetchone()[0] == "ok"
n = c.execute("select count(*) from generations").fetchone()[0]
print("constant.db n=", n)
print(c.execute("select lang, config, count(*) from generations group by 1,2").fetchall())
if n < 900:
    raise SystemExit(f"too few rows: {n} (need 900 for chain)")
print("VERIFY_OK")
PY
then
  say "VERIFY FAILED"
  exit 1
fi
ssh $ssh_opts -p "$PORT" root@"$IP" 'touch /workspace/SYNCED && echo SYNCED'
say "PULL_OK SYNCED"
# Guide §12: SYNCED race — API stop is what actually ends the GPU bill.
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 -X POST -H "$AUTH" \
  "https://rest.runpod.io/v1/pods/$POD/stop")
say "stop request -> HTTP $code"
exit 0
