#!/bin/bash
# G2b + w32 — the follow-ups G2 and the positioning research demanded.
#
# Usage:  e_day3c.sh w32     (2,400 gens, ~5h)   -> results/w32.db
#         e_day3c.sh pad     (1,600 gens, ~3.5h) -> results/pad384.db
#
# Split into two blocks on purpose: measured throughput (2026-08-13) says the
# whole chain is ~9h on one pod, which would land at 04:00. Run the blocks on
# the two pods as they free instead — w32 first, since it is the sharpest cell.
#
# Why these exist:
# G2 at decode cap 128 showed the predicted signature — natural English exactly
# null (0.0pp, 1 fixed / 1 broken), English padded to fill the 64-token window
# damaged -9.0pp (2/11, p=0.022), healed +6.0pp by widening to w128 (7/1). But
# restricting to items untruncated in both arms collapsed the damage to -1.2pp,
# so the channel is entangled with the output cap. That restriction is a
# COLLIDER (compression plausibly causes the rambling that causes truncation),
# so it cannot settle the question. A higher cap can: at 384 a model that merely
# rambles still reaches its answer, so surviving damage is lost knowledge.
#
# Fresh dbs — run_keys do not include the decode cap.
# Self-stop markers: ALL_DAY3C_W32_DONE / ALL_DAY3C_PAD_DONE
# UV_NO_SYNC is not optional: pod C2 runs a hand-pinned torch 2.11.0+cu128
# because its driver is CUDA 12.8, and an implicit `uv sync` would install the
# lockfile's cu130 build over it and break model loading. Harmless on the other
# pods, so it is set unconditionally rather than remembered per-pod.
export HF_HOME=/workspace/hf PATH=$HOME/.local/bin:$PATH UV_NO_SYNC=1
cd /workspace/mlkv
BLOCK=${1:?usage: e_day3c.sh w32|pad}
LOG=/workspace/day3c_$BLOCK.log
M=Qwen/Qwen3-4B

say() { echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }
snap() {
  rm -f "results/$1-snapshot.db"
  python3 -c "
import sqlite3
c = sqlite3.connect('results/$1.db')
c.execute(\"VACUUM INTO 'results/$1-snapshot.db'\")
print('$1', c.execute('SELECT COUNT(*) FROM generations').fetchone()[0], 'rows')
" >> "$LOG" 2>&1
}

say "=== day3c block=$BLOCK start, HEAD $(git rev-parse --short HEAD)"

if [ "$BLOCK" = "w32" ]; then
  # The constant operators actually get. TensorRT-LLM's RocketKV backend ships
  # _get_snapkv_indices with q_obs = q[:, :, -window_size:] and a default
  # window_size of 32 (docs/positioning-2026-08-13.md) — HALF the kvpress value
  # we tested. Against measured Qwen3 instruction lengths (en 19, th 33, sw 34,
  # bn 73) a 32-token window is exceeded by every language except English.
  # In the instr-last layout the window holds [.. question, instruction]: at w64
  # Thai spends 33 tokens on instruction and still has ~31 tokens of QUESTION
  # visible, which is why th/sw are safe there. At w32 the window is 32/33
  # instruction tokens and ZERO question tokens — blind.
  # REGISTERED PREDICTION: th and sw, which carry "no effect" verdicts at w64,
  # break at w32; English (19 tokens, still fits) stays flat; bn breaks at both.
  # If th/sw do NOT break at w32, the threshold account is wrong — report it.
  # 200 paired items per cell: G2-sized effects at n=100 leave p at 0.02-0.07,
  # not enough for the cell that carries the title.
  uv run mlkv run --model $M --task mrag --langs en,th,sw,bn --ctx 8k,16k \
    --configs baseline,snapkv@r0.75:w32,snapkv@r0.75 \
    --max-items 100 --max-new-tokens 384 --db results/w32.db 2>&1 | tail -1 >> "$LOG"
  say W32_DONE
  snap w32
  say ALL_DAY3C_W32_DONE

elif [ "$BLOCK" = "pad" ]; then
  # Natural-length English at cap 384 — the control everything rests on.
  uv run mlkv run --model $M --task mrag --langs en --ctx 8k \
    --configs baseline,snapkv@r0.75,snapkv@r0.9375 \
    --max-items 100 --max-new-tokens 384 --db results/pad384.db 2>&1 | tail -1 >> "$LOG"
  say G2B_NATURAL_DONE

  # PAD48 localizes the cliff. G2 has instruction 19 (safe) and 64 (broken)
  # with a 45-token evidence gap, leaving room for "prepended filler itself
  # hurts under compression". A 48-token instruction still FITS the window, so
  # the registered prediction is NO damage: pad48 safe + pad64 broken puts the
  # cliff in [48,64], where the constant is. If pad48 breaks too, the
  # padding-per-se account wins and the window story weakens — report it.
  uv run mlkv run --model $M --task mrag --langs en --ctx 8k \
    --configs baseline,snapkv@r0.75 --mrag-instr-pad 48 \
    --max-items 100 --max-new-tokens 384 --db results/pad384.db 2>&1 | tail -1 >> "$LOG"
  say PAD48_DONE

  # Padded English at both doses. Filler is prepended, so in every padded cell
  # the window's tail is the original 19-token spec and the passages are already
  # outside it — blindness saturates at pad 64, which is why the cap-128 dose
  # curve was flat in the compressed arm (86/86/87) rather than monotone.
  # r0.9375 is included because English's 93-95% baseline leaves only ~6pp of
  # headroom at r0.75; the heavy dose has room the light dose lacks.
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
  snap pad384
  say ALL_DAY3C_PAD_DONE

else
  say "unknown block: $BLOCK"; exit 1
fi
