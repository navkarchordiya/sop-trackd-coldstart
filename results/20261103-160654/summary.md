# Cold-start benchmark summary (run 20261103-160654)

- Host: Darwin 27.2.0 arm64; Docker 28.3.2 (linux/arm64); VM: 8 CPUs, 4109803520 bytes RAM
- Image coldstart-fn:1.0: 50.5 MB
- 50 measured trials per condition (+3 warm-up each, discarded); order shuffled with seed 6
- Polling interval 5 ms (resolution of cold/thawed timings)

## Time to first successful response (ms)

| condition | n | mean | stdev | min | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|---|---|
| cold | 50 | 124.6 | 10.2 | 109.6 | 122.9 | 133.6 | 138.7 | 174.7 |
| thawed | 50 | 29.4 | 5.8 | 20.9 | 28.2 | 38.3 | 39.7 | 46.2 |
| warm | 50 | 1.6 | 0.6 | 0.5 | 1.6 | 2.3 | 2.4 | 3.1 |

## Differences of medians, with 95% bootstrap CI (seed 6)

| comparison | difference (ms) | ratio | 95% CI (ms) |
|---|---|---|---|
| cold_minus_warm | +121.3 | 77.0x | [+119.8, +123.2] |
| thawed_minus_warm | +26.6 | 17.7x | [+24.7, +28.2] |
| cold_minus_thawed | +94.7 | 4.4x | [+92.3, +97.2] |

## Where a cold start's time goes (medians, ms)

- `docker run -d` command returned after: 106.7 (of which plain docker CLI overhead, from a trivial `docker inspect`: 14.1)
- Python app init inside the container (imports + bind socket): 19.4
- From `docker run` returning to the first response (Python start-up + the app init above + port publishing + up to one poll interval): 16.2
- First cold starts of the session (warm-up, not in the table): 161, 124, 111
