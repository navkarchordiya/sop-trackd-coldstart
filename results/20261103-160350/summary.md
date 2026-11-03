# Cold-start benchmark summary (run 20261103-160350)

- Host: Darwin 27.2.0 arm64; Docker 28.3.2 (linux/arm64); VM: 8 CPUs, 4109803520 bytes RAM
- Image coldstart-fn:1.0: 43.6 MB
- 50 measured trials per condition (+3 warm-up each, discarded); order shuffled with seed 6
- Polling interval 5 ms (resolution of cold/thawed timings)

## Time to first successful response (ms)

| condition | n | mean | stdev | min | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|---|---|
| cold | 50 | 237.1 | 7.9 | 221.5 | 236.6 | 244.8 | 250.1 | 262.1 |
| thawed | 50 | 27.3 | 3.2 | 21.9 | 27.9 | 31.5 | 32.0 | 32.6 |
| warm | 50 | 1.6 | 0.5 | 0.6 | 1.4 | 2.2 | 2.3 | 2.7 |

## Differences of medians, with 95% bootstrap CI (seed 6)

| comparison | difference (ms) | ratio | 95% CI (ms) |
|---|---|---|---|
| cold_minus_warm | +235.2 | 169.9x | [+233.3, +238.0] |
| thawed_minus_warm | +26.6 | 20.1x | [+23.6, +28.2] |
| cold_minus_thawed | +208.6 | 8.5x | [+206.3, +212.9] |

## Where a cold start's time goes (medians, ms)

- `docker run -d` command returned after: 108.8 (of which plain docker CLI overhead, from a trivial `docker inspect`: 14.5)
- Python app init inside the container (imports + bind socket): 124.0
- From `docker run` returning to the first response (Python start-up + the app init above + port publishing + up to one poll interval): 127.8
- First cold starts of the session (warm-up, not in the table): 252, 237, 232
