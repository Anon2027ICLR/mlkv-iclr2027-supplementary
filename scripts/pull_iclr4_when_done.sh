#!/bin/bash
# Local puller for e_iclr4 (bn_ladder / agnostic / ratio).
set -u
POD="${POD:-}"
DEST="${DEST:-$HOME/working_space/research/mlkv/results}"
LOG="${LOG:-$HOME/working_space/research/mlkv/results/pull_iclr4.log}"
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
      if grep -q ALL_ICLR4_ALL_DONE /workspace/iclr4_all.log 2>/dev/null; then echo DONE; exit 0; fi
      if grep -q ALL_ICLR4_CHAIN_DONE /workspace/iclr4_chain.log 2>/dev/null \
         && ! pgrep -f "e_iclr4.sh|run_iclr4_all" >/dev/null; then
        echo DONE
        exit 0
      fi
      python3 -c "
import sqlite3, os
def n(p):
    return sqlite3.connect(p).execute(\"select count(*) from generations\").fetchone()[0] if os.path.exists(p) else 0
print(\"rows v_trace_bn=%d agnostic=%d ratio=%d\" % (
    n(\"/workspace/mlkv/results/v_trace_bn.db\"),
    n(\"/workspace/mlkv/results/agnostic.db\"),
    n(\"/workspace/mlkv/results/ratio.db\")))
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
for f in v_trace_bn.db v_trace_bn-snapshot.db v_trace_bn-final.db \
         agnostic.db agnostic-snapshot.db agnostic-final.db \
         ratio.db ratio-snapshot.db ratio-final.db; do
  scp -q -P "$PORT" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30 \
    root@"$IP":/workspace/mlkv/results/$f "$DEST/${f}.part" 2>>"$LOG" || true
  if [ -f "$DEST/${f}.part" ]; then
    mv "$DEST/${f}.part" "$DEST/$f"
  fi
done

if ! python3 - "$DEST" <<'PY' >>"$LOG" 2>&1
import sqlite3, sys, os
dest = sys.argv[1]
ok = True
need = {"v_trace_bn.db": 600, "agnostic.db": 600, "ratio.db": 800}
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
