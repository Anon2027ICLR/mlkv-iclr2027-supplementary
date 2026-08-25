#!/bin/bash
# Local puller for e_iclr10 (fifth-review Group B: refine, oracle_depth,
# ctx16k; qwen32b via STORES override). After a verified pull: touch SYNCED, then
# POST /pods/$POD/stop (guide §12). Also pulls the chain log.
set -u
POD="${POD:-}"
DEST="${DEST:-$HOME/working_space/research/mlkv/results}"
LOG="${LOG:-$HOME/working_space/research/mlkv/results/pull_iclr10.log}"
AUTH="Authorization: Bearer $(cat "$HOME/.config/runpod/api_key")"
mkdir -p "$DEST"
say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
ssh_opts="-n -o StrictHostKeyChecking=accept-new -o ConnectTimeout=12 -o BatchMode=yes"

# store -> expected generations rows
# refine: 100 x 2 x 2 = 400; oracle_depth: 669 x 3 = 2007;
# ctx16k: 100 x 3 = 300. (qwen32b:600 pulls from its own pod: set STORES=qwen32b:600.)
STORES="${STORES:-refine:400 oracle_depth:2007 ctx16k:300}"

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
      if grep -q ALL_ICLR10_CHAIN_DONE /workspace/iclr10_chain.log 2>/dev/null; then
        echo DONE; exit 0
      fi
      python3 - <<PY
import sqlite3, os
for s in ["slack_depth", "xinstr", "if_depth", "thsw"]:
    p = f"/workspace/mlkv/results/{s}.db"
    n = (sqlite3.connect(p).execute("select count(*) from generations")
         .fetchone()[0] if os.path.exists(p) else 0)
    print(f"rows {s}={n}")
PY
    ' 2>/dev/null || echo FAIL)
    say "remote: $info"
    if echo "$info" | grep -q DONE; then
      break
    fi
  fi
  sleep 180
done

say "pulling"
for entry in $STORES; do
  s="${entry%%:*}"
  for f in "$s.db" "$s-snapshot.db"; do
    scp -q -P "$PORT" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30 \
      root@"$IP":/workspace/mlkv/results/$f "$DEST/${f}.part" 2>>"$LOG" || true
    if [ -f "$DEST/${f}.part" ]; then
      mv "$DEST/${f}.part" "$DEST/$f"
    fi
  done
done
# Do not overwrite the locked local q_percentiles.json: keep the pod copy
# under a distinct name for the provenance record.
scp -q -P "$PORT" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30 \
  root@"$IP":/workspace/mlkv/results/q_percentiles.json \
  "$DEST/q_percentiles_iclr10.json.part" 2>>"$LOG" || true
if [ -f "$DEST/q_percentiles_iclr10.json.part" ]; then
  mv "$DEST/q_percentiles_iclr10.json.part" "$DEST/q_percentiles_iclr10.json"
fi
scp -q -P "$PORT" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30 \
  root@"$IP":/workspace/iclr10_chain.log "$DEST/iclr10_chain.log.part" 2>>"$LOG" || true
if [ -f "$DEST/iclr10_chain.log.part" ]; then
  mv "$DEST/iclr10_chain.log.part" "$DEST/iclr10_chain.log"
fi

if ! python3 - "$DEST" <<'PY' >>"$LOG" 2>&1
import sqlite3, sys, os
dest = sys.argv[1]
EXPECT = {"slack_depth": 2676, "xinstr": 600, "if_depth": 1338, "thsw": 600}
for s, want in EXPECT.items():
    p = os.path.join(dest, f"{s}.db")
    c = sqlite3.connect(p)
    assert c.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    n = c.execute("select count(*) from generations").fetchone()[0]
    print(s, "n=", n)
    print(c.execute(
        "select lang, config, count(*) from generations group by 1,2").fetchall())
    if n < want:
        raise SystemExit(f"{s}: too few rows: {n} (need {want})")
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
