#!/bin/bash
# Operator-side status for the ICLR slot. Never scp a live db.
# Usage: iclr_watch.sh [pod_id ...]
set -u
AUTH="Authorization: Bearer $(cat ~/.config/runpod/api_key)"
IDS=${*:-r948gmdyb92lxo cnyygicgfyr9w6 4y67x49gy9gvlg}

rp() { curl -s --max-time 20 -H "$AUTH" "https://rest.runpod.io/v1$1"; }

echo "=== $(date -u +%FT%TZ) ==="
curl -s --max-time 20 -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"query":"query { myself { clientBalance currentSpendPerHr } }"}' \
  https://api.runpod.io/graphql \
  | python3 -c "import json,sys
m=json.load(sys.stdin).get('data',{}).get('myself',{})
print(f\"balance \${m.get('clientBalance',0):.2f}  spend \${m.get('currentSpendPerHr',0)}/hr\")"

for id in $IDS; do
  js=$(rp /pods/$id)
  eval "$(python3 -c "
import json,sys
d=json.loads(sys.argv[1])
pm=d.get('portMappings') or {}
print(f\"name={d.get('name')!r}\")
print(f\"status={d.get('desiredStatus')!r}\")
print(f\"ip={d.get('publicIp') or ''!r}\")
print(f\"port={pm.get('22') or ''!r}\")
print(f\"cost={d.get('costPerHr')!r}\")
" "$js")"
  echo "-- $name $id $status \$$cost/hr"
  if [ "$status" != "RUNNING" ] || [ -z "$ip" ] || [ -z "$port" ]; then
    echo "   no ssh"
    continue
  fi
  ssh -n -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -p "$port" root@"$ip" '
    echo "   driver: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)"
    echo "   watchdogs: $(ps -eo args | grep -c "^bash /workspace/mlkv/scripts/self_sto[p]\.sh" || true)"
    echo "   drivers: $(ps -eo args | grep -c "e_iclr\.sh" || true)"
    for f in /workspace/iclr_*.log; do
      [ -f "$f" ] || continue
      echo "   log $(basename $f): $(tail -1 "$f" 2>/dev/null)"
    done
    cd /workspace/mlkv 2>/dev/null || exit 0
    python3 - <<PY
import sqlite3, glob, os
for p in sorted(glob.glob("results/{cliff_en,cliff_multi,autowin,cliff_gemma,schema}.db")):
    try:
        n=sqlite3.connect(p).execute("SELECT COUNT(*) FROM generations").fetchone()[0]
        print(f"   rows {os.path.basename(p)} {n}")
    except Exception as e:
        print(f"   rows {os.path.basename(p)} ERR {e}")
PY
    for m in ALL_ICLR_A_DONE ALL_ICLR_B_DONE ALL_ICLR_C_DONE ALL_ICLR_CLIFF_EN_DONE ALL_ICLR_CLIFF_MULTI_DONE ALL_ICLR_AUTOWIN_DONE ALL_ICLR_GEMMA_DONE ALL_ICLR_SCHEMA_DONE; do
      grep -l "$m" /workspace/iclr_*.log 2>/dev/null | sed "s|.*/|   MARKER $m in |"
    done
  ' || echo "   ssh failed"
done
