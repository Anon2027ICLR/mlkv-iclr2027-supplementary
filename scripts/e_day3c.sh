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
# Self-stop marker: ALL_DAY3C_DONE, dbs: pad384,w32
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

# W32 — the constant operators actually get. TensorRT-LLM's RocketKV backend
# ships _get_snapkv_indices with q_obs = q[:, :, -window_size:] and a default
# window_size of 32 (docs/positioning-2026-08-13.md). That is HALF the kvpress
# default we have been testing, and against measured instruction lengths on the
# Qwen3 tokenizer (en 19, th 33, sw 34, bn 73, te 105) it is exceeded by every
# language except English. Registered prediction: at w32 the threshold moves
# down, so th and sw — which are safe at w64 — now take damage, while English
# (19 tokens, still fits) stays flat. If th/sw do NOT break at w32, the
# threshold account is wrong and must be reported.
uv run mlkv run --model $M --task mrag --langs en,th,sw,bn --ctx 8k,16k \
  --configs baseline,snapkv@r0.75:w32,snapkv@r0.75 \
  --max-items 100 --max-new-tokens 384 --db results/w32.db 2>&1 | tail -1 >> "$LOG"
say W32_DONE

# PAD48 — localize the cliff. G2 has instruction 19 (safe) and 64 (broken)
# with a 45-token evidence gap between them, leaving room for the alternative
# reading "prepended filler itself hurts under compression". A 48-token padded
# instruction still fits the 64-token window, so the registered prediction is
# NO damage. pad48 safe + pad64 broken localizes the cliff to [48, 64] — right
# where the constant sits. If pad48 breaks too, the padding-per-se account
# wins and the window story weakens: report either way.
uv run mlkv run --model $M --task mrag --langs en --ctx 8k \
  --configs baseline,snapkv@r0.75 --mrag-instr-pad 48 \
  --max-items 100 --max-new-tokens 384 --db results/pad384.db 2>&1 | tail -1 >> "$LOG"
say PAD48_DONE

for db in pad384 w32; do
  rm -f "results/$db-snapshot.db"
  python3 -c "
import sqlite3
c = sqlite3.connect('results/$db.db')
c.execute(\"VACUUM INTO 'results/$db-snapshot.db'\")
print('$db', c.execute('SELECT COUNT(*) FROM generations').fetchone()[0], 'rows')
" >> "$LOG" 2>&1
done
say ALL_DAY3C_DONE
