#!/bin/bash
# Local puller for the 2026-08-17 review-response arms (e_iclr3).
# Waits for ALL_ICLR3_CHAIN_DONE (or the last optional marker if present),
# then scp + verify + touch /workspace/SYNCED.
set -u
POD="${POD:?set POD to the new pod id}"
DEST="${DEST:-$HOME/working_space/research/mlkv/results}"
LOG="${LOG:-$HOME/working_space/research/mlkv/results/pull_iclr3.log}"
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
      # Prefer the wrapper-all marker; fall back to chain if extras never ran.
      if grep -q ALL_ICLR3_ALL_DONE /workspace/iclr3_all.log 2>/dev/null; then echo DONE; exit 0; fi
      if grep -q ALL_ICLR3_CHAIN_DONE /workspace/iclr3_chain.log 2>/dev/null \
         && ! pgrep -f "e_iclr3.sh|run_iclr3_all" >/dev/null; then
        echo DONE
        exit 0
      fi
      python3 -c "
import sqlite3, os
def n(p):
    return sqlite3.connect(p).execute(\"select count(*) from generations\").fetchone()[0] if os.path.exists(p) else 0
print(f\"rows llama={n(\"/workspace/mlkv/results/llama.db\")} instr_first={n(\"/workspace/mlkv/results/instr_first.db\")}\")
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
for f in llama.db llama-snapshot.db llama-final.db \
         instr_first.db instr_first-snapshot.db instr_first-final.db \
         q_percentiles_llama.json; do
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
# llama: 600 (en+bn) or 900 (+te)
p = os.path.join(dest, "llama.db")
c = sqlite3.connect(p)
assert c.execute("PRAGMA quick_check").fetchone()[0] == "ok"
n = c.execute("select count(*) from generations").fetchone()[0]
print("llama.db n=", n)
print(c.execute("select lang, config, count(*) from generations group by 1,2").fetchall())
if n < 600:
    print("TOO FEW llama", n)
    ok = False
p = os.path.join(dest, "instr_first.db")
c = sqlite3.connect(p)
assert c.execute("PRAGMA quick_check").fetchone()[0] == "ok"
n = c.execute("select count(*) from generations").fetchone()[0]
print("instr_first.db n=", n)
print(c.execute("select lang, config, count(*) from generations group by 1,2").fetchall())
if n < 600:
    print("TOO FEW instr_first", n)
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
