# ICLR6 `pool_check` excerpt (from the campaign pod)

Pulled 2026-08-18T16:27Z from `/workspace/iclr6_chain.log` on
`mlkv-iclr6` (`297ccl21a2urwe`) after the chain had finished. Driver:
`scripts/e_iclr6.sh chain` at HEAD `e287172`. Full log is 121812 bytes;
only the pool-scoping block is archived here.

The `te` print is interleaved with `tee` (stdout + stderr +
`POOL_CHECK_DONE` on one line). The format string in `e_iclr6.sh` is
`"{code}: TyDiQA-GoldP validation pool = {n} items (current eval uses
[:100]; extension headroom = {n-100})"`, so Telugu's intended line is
669 items / headroom 569. The same process then logged mRAG pool sizes
independently: bn 113, te 669.

```
2026-08-18T13:33:11Z === preflight HEAD e287172 UV_NO_SYNC=1
2026-08-18T13:34:12Z === pool_check (W4 scoping; zero generations)
bn: TyDiQA-GoldP validation pool = 113 items (current eval uses [:100]; extension headroom = 13)
te: TyDiQA-GoldP validation pool = 669 bn: TyDiQA-GoldP validation pool = 113 items (current eval 2026-08-18T13:34:26Z POOL_CHECK_DONE
2026-08-18T13:34:26Z === main start (constant w=256 at r=0.75 + random-eviction control)
INFO mlkv.tasks.mrag: mrag[en]: pool ready (1190 questions, 10156 passages)
INFO mlkv.tasks.mrag: mrag[bn]: pool ready (113 questions, 1870 passages)
WARNING mlkv.tasks.mrag: mrag[bn]: only 113 questions available (wanted 300)
INFO mlkv.tasks.mrag: mrag[te]: pool ready (669 questions, 4935 passages)
```
