#!/bin/bash
# G2b — rerun the padded-instruction identification experiment at decode cap 384.
#
# Why this exists (2026-08-13, after G2 read out at cap 128):
# G2 showed the predicted signature — natural English exactly null (0.0pp, 1
# fixed / 1 broken), English padded to fill the 64-token window damaged −9.0pp
# (2 fixed / 11 broken, p=0.022), and healed +6.0pp by widening to w128 (7
# fixed / 1 broken, p=0.070). But restricting to items untruncated in both
# conditions collapsed the damage to −1.2pp, so the channel is entangled with
# the 128-token output cap. That restriction is a COLLIDER (compression may
# cause the rambling that causes truncation), so it cannot settle the question
# either way. Raising the cap can: at 384 a model that merely rambles still
# reaches its answer, so any surviving damage is lost knowledge, not lost room.
#
# Also adds the heavy dose: English's baseline sits at 93-95%, which bounds how
# much r0.75 can take away. r0.9375 has room to show the effect if it is real.
#
# Fresh db — run_keys do not include the decode cap.
# Launch:  setsid bash /workspace/mlkv/scripts/e_day3c.sh &
# Self-stop marker: ALL_DAY3C_DONE, db: pad384
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH
cd /workspace/mlkv
LOG=/workspace/day3c.log
M=Qwen/Qwen3-4B

say() { echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }

say "=== day3c (G2b) chain start"
say "HEAD $(git rev-parse --short HEAD)"

# Natural-length English at cap 384 — the control the whole comparison rests on.
uv run mlkv run --model $M --task mrag --langs en --ctx 8k \
  --configs baseline,snapkv@r0.75,snapkv@r0.9375 \
  --max-items 100 --max-new-tokens 384 --db results/pad384.db 2>&1 | tail -1 >> "$LOG"
say G2B_NATURAL_DONE

# Padded English at both doses. Padding is prepended, so in every padded cell
# the window's tail is the original 19-token spec and the passages are outside
# it — blindness saturates at pad 64, which is why the cap-128 dose curve was
# flat in the compressed arm (86/86/87) rather than monotone.
for pad in 64 96 128; do
  uv run mlkv run --model $M --task mrag --langs en --ctx 8k \
    --configs baseline,snapkv@r0.75,snapkv@r0.9375 --mrag-instr-pad $pad \
    --max-items 100 --max-new-tokens 384 --db results/pad384.db 2>&1 | tail -1 >> "$LOG"
done
say G2B_PADDED_DONE

# The cliff must move with the constant, at both doses.
uv run mlkv run --model $M --task mrag --langs en --ctx 8k \
  --configs snapkv@r0.75:w128,snapkv@r0.9375:w128 --mrag-instr-pad 96 \
  --max-items 100 --max-new-tokens 384 --db results/pad384.db 2>&1 | tail -1 >> "$LOG"
say G2B_HEAL_DONE

rm -f results/pad384-snapshot.db
python3 -c "
import sqlite3
c = sqlite3.connect('results/pad384.db')
c.execute(\"VACUUM INTO 'results/pad384-snapshot.db'\")
print('pad384', c.execute('SELECT COUNT(*) FROM generations').fetchone()[0], 'rows')
" >> "$LOG" 2>&1
say ALL_DAY3C_DONE
