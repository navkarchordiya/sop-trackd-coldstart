# Cold-start benchmark summary (run 20261103-160321)

- Host: Darwin 27.2.0 arm64; Docker 28.3.2 (linux/arm64); VM: 8 CPUs, 4109803520 bytes RAM
- Image coldstart-fn:1.0: 43.6 MB
- 50 measured trials per condition (+3 warm-up each, discarded); order shuffled with seed 6
- Polling interval 5 ms (resolution of cold/thawed timings)

## Time to first successful response (ms)

| condition | n | mean | stdev | min | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|---|---|
| cold | 50 | 238.9 | 18.2 | 215.3 | 237.0 | 248.1 | 250.7 | 334.5 |
| thawed | 50 | 30.5 | 6.8 | 22.8 | 29.6 | 37.6 | 41.0 | 60.6 |
| warm | 50 | 1.6 | 0.7 | 0.6 | 1.4 | 2.5 | 3.2 | 3.5 |

## Differences of medians, with 95% bootstrap CI (seed 6)

| comparison | difference (ms) | ratio | 95% CI (ms) |
|---|---|---|---|
| cold_minus_warm | +235.5 | 163.7x | [+233.2, +238.7] |
| thawed_minus_warm | +28.1 | 20.4x | [+25.4, +29.0] |
| cold_minus_thawed | +207.4 | 8.0x | [+205.3, +211.1] |

## Where a cold start's time goes (medians, ms)

- `docker run -d` command returned after: 109.0 (of which plain docker CLI overhead, from a trivial `docker inspect`: 14.5)
- Python app init inside the container (imports + bind socket): 123.7
- From `docker run` returning to the first response (Python start-up + the app init above + port publishing + up to one poll interval): 128.0
- First cold starts of the session (warm-up, not in the table): 257, 223, 222
