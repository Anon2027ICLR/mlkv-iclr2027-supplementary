#!/bin/bash
# Local puller for e_iclr7 (full TyDiQA-GoldP validation pool depth).
# After a verified pull: touch SYNCED, then POST /pods/$POD/stop (guide §12).
# Also pulls the chain log so guards/pool sizes land in the repo.
set -u
POD="${POD:-}"
DEST="${DEST:-$HOME/working_space/research/mlkv/results}"
LOG="${LOG:-$HOME/working_space/research/mlkv/results/pull_iclr7.log}"
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
      # te-resume: ignore stale ALL_ICLR7_CHAIN_DONE in iclr7_chain.log
      # (that marker was written at 1239 rows). Wait for DEPTH_te_DONE,
      # which the driver writes after VACUUM INTO snapshot.
      if grep -q DEPTH_te_DONE /workspace/iclr7_te.log 2>/dev/null; then
        n=$(python3 -c "import sqlite3,os; p=\"/workspace/mlkv/results/depth.db\"; print(sqlite3.connect(p).execute(\"select count(*) from generations\").fetchone()[0] if os.path.exists(p) else 0)")
        if [ "$n" -ge 2346 ]; then echo DONE; exit 0; fi
        echo "MARKER_BUT_ROWS=$n"
        exit 0
      fi
      python3 -c "
import sqlite3, os
p=\"/workspace/mlkv/results/depth.db\"
n=sqlite3.connect(p).execute(\"select count(*) from generations\").fetchone()[0] if os.path.exists(p) else 0
print(f\"rows depth={n}\")
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
for f in depth.db depth-snapshot.db depth-final.db; do
  scp -q -P "$PORT" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30 \
    root@"$IP":/workspace/mlkv/results/$f "$DEST/${f}.part" 2>>"$LOG" || true
  if [ -f "$DEST/${f}.part" ]; then
    mv "$DEST/${f}.part" "$DEST/$f"
  fi
done
# Do not overwrite the locked Qwen q_percentiles.json.
scp -q -P "$PORT" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30 \
  root@"$IP":/workspace/mlkv/results/q_percentiles.json \
  "$DEST/q_percentiles_iclr7.json.part" 2>>"$LOG" || true
if [ -f "$DEST/q_percentiles_iclr7.json.part" ]; then
  mv "$DEST/q_percentiles_iclr7.json.part" "$DEST/q_percentiles_iclr7.json"
fi
# Chain log (guards + pool sizes). Copy to docs as .md later if needed;
# results/*.log is gitignored so also keep a named copy under /tmp.
scp -q -P "$PORT" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30 \
  root@"$IP":/workspace/iclr7_chain.log "$DEST/iclr7_chain.log.part" 2>>"$LOG" || true
if [ -f "$DEST/iclr7_chain.log.part" ]; then
  mv "$DEST/iclr7_chain.log.part" "$DEST/iclr7_chain.log"
fi

if ! python3 - "$DEST" <<'PY' >>"$LOG" 2>&1
import sqlite3, sys, os
dest = sys.argv[1]
p = os.path.join(dest, "depth.db")
c = sqlite3.connect(p)
assert c.execute("PRAGMA quick_check").fetchone()[0] == "ok"
n = c.execute("select count(*) from generations").fetchone()[0]
print("depth.db n=", n)
print(c.execute("select lang, config, count(*) from generations group by 1,2").fetchall())
# te 669*3 + bn 113*3 = 2346
if n < 2346:
    raise SystemExit(f"too few rows: {n} (need 2346 for chain)")
print("VERIFY_OK")
PY
then
  say "VERIFY FAILED"
  exit 1
fi
ssh $ssh_opts -p "$PORT" root@"$IP" 'touch /workspace/SYNCED && echo SYNCED'
say "PULL_OK SYNCED"
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 -X POST -H "$AUTH" \
  "https://rest.runpod.io/v1/pods/$POD/stop")
say "stop request -> HTTP $code"
exit 0
