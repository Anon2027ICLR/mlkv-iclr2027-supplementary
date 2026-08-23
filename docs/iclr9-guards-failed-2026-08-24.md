# iclr9 chain: GUARDS_FAILED abort log (2026-08-24, verbatim)

Raw pod log, zero generations produced. See the amendment in
iclr-thsw-preregister.md.

```
2026-08-23T16:09:28Z === preflight HEAD 96bd5e2 UV_NO_SYNC=1
2026-08-23T16:09:31Z === guards: TyDiQA pools + id disjointness (depth-arm guard, sw added)
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits andWarning: You are seGenerating train split:   0%|          | 0/49881 [00:00<?, ? examples/s]Generating train split:   2%|▏         | 1000/49881 [00:00<00:13, 3571.71 examples/s]Generating train split:  24%|██▍       | 12000/49881 [00:00<00:01, 37156.91 examples/s]Generating train split:  46%|████▌     | 23000/49881 [00:00<00:00, 57717.75 examples/s]Generating train split:  74%|███████▍  | 37000/49881 [00:00<00:00, 80036.65 examples/s]Generating train split: 100%|██████████| 49881/49881 [00:00<00:00, 61414.65 examples/s]
Generating validation split:   0%|          | 0/5077 [00:00<?, ? examples/s]Generating validation split: 100%|██████████| 5077/5077 [00:00<00:00, 49863.32 examples/s]
bengali: validation=113 train=2390 raw-overlap=3
  eval(full pool) ∩ Q90-source = 0: the held-out discipline holds
tebengali: validation=113 train=2390 raw-overlap=3
  eval(full pool) ∩ Q90-source = 0: the held-out discipline holds
telugu: validation=669 train=5563 raw-overlap=0
  eval(full pool) ∩ Q90-source = 0: the held-out discipline holds
swahili: validation=499 train=2755 raw-overlap=2
FATAL: unexpected r2026-08-23T16:09:59Z GUARDS_FAILED -- aborting
es: ['swahili--1339720473726915592-0', 'swahili-1422153578110398972-3']
2026-08-23T16:09:59Z GUARDS_FAILED -- aborting
```
