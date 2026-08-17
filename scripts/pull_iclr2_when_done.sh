#!/bin/bash
# Local puller for the 2026-08-17 ICLR follow-up arms.
# Waits for ALL_ICLR2_GEMMA_Q90_DONE (last block) or the three target
# row counts, VACUUM-style files already snapshotted on-pod, then scp
# + verify + touch /workspace/SYNCED.
set -u
POD="${POD:-63izxi6eawobaj}"
DEST="${DEST:-$HOME/working_space/research/mlkv/results}"
LOG="${LOG:-$HOME/working_space/research/mlkv/results/pull_iclr2.log}"
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
      if grep -q ALL_ICLR2_GEMMA_Q90_DONE /workspace/iclr2_gemma_q90.log 2>/dev/null; then
        echo DONE
        exit 0
      fi
      python3 -c "
import sqlite3, os
def n(p):
    return sqlite3.connect(p).execute(\"select count(*) from generations\").fetchone()[0] if os.path.exists(p) else 0
s, v, g = n(\"/workspace/mlkv/results/schema_fix.db\"), n(\"/workspace/mlkv/results/v_trace.db\"), n(\"/workspace/mlkv/results/gemma_q90.db\")
print(f\"rows schema_fix={s} v_trace={v} gemma_q90={g}\")
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
for f in schema_fix.db schema_fix-snapshot.db schema_fix-final.db \
         v_trace.db v_trace-snapshot.db v_trace-final.db \
         gemma_q90.db gemma_q90-snapshot.db gemma_q90-final.db \
         q_percentiles_gemma.json; do
  scp -q -P "$PORT" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30 \
    root@"$IP":/workspace/mlkv/results/$f "$DEST/${f}.part" 2>>"$LOG" || true
  if [ -f "$DEST/${f}.part" ]; then
    mv "$DEST/${f}.part" "$DEST/$f"
  fi
done

if ! python3 - "$DEST" <<'PY' >>"$LOG" 2>&1
import sqlite3, sys, os
dest = sys.argv[1]
need = {"schema_fix.db": 900, "gemma_q90.db": 900}
# v_trace is 600 (te only) or 1200 (te+bn)
ok = True
for name, lo in need.items():
    p = os.path.join(dest, name)
    c = sqlite3.connect(p)
    assert c.execute("PRAGMA quick_check").fetchone()[0] == "ok", name
    n = c.execute("select count(*) from generations").fetchone()[0]
    print(name, "n=", n)
    print(c.execute("select lang, config, count(*) from generations group by 1,2").fetchall())
    if n < lo:
        print("TOO FEW", name, n)
        ok = False
p = os.path.join(dest, "v_trace.db")
c = sqlite3.connect(p)
assert c.execute("PRAGMA quick_check").fetchone()[0] == "ok"
n = c.execute("select count(*) from generations").fetchone()[0]
print("v_trace.db n=", n)
print(c.execute("select lang, config, count(*) from generations group by 1,2").fetchall())
if n < 600:
    print("TOO FEW v_trace", n)
    ok = False
if not ok:
    raise SystemExit("verify failed")
print("VERIFY_OK")
PY
then
  say "VERIFY FAILED"
  exit 1
fi
ssh $ssh_opts -p "$PORT" root@"$IP" 'touch /workspace/SYNCED && echo SYNCED'
say "PULL_OK SYNCED"
exit 0
