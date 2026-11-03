# Track D: Cold-start vs pre-warmed latency of a containerised serverless-style function

SOP trial task for Dr. K Hari Babu, Track D. Navkar Chordiya, ID 2023B3A71006P. **Random seed: 6.**

**Result:** median cold start 237 ms vs 1.4 ms warm (pre-warmed) and 28 ms thawed. Most of the cold start was Python recompiling its standard library; precompiling `.pyc` files in the image halved it to 123 ms. Full write-up: [docs/REPORT.md](docs/REPORT.md).

**Question:** how much slower is the first request when the function's container has to start from nothing (cold), or be unfrozen (thawed), compared with a pre-warmed container that is already running?

| condition | what happens before the request |
|---|---|
| cold | `docker run` a brand-new container, then poll until the function answers |
| thawed | the container exists but is frozen (`docker pause`, cgroup freezer, like Lambda freezing an idle environment). `docker unpause`, then request |
| warm | container already running (pre-warmed). Just request |

50 measured trials per condition, after 3 warm-up trials each that are discarded. All 150 trials are shuffled together with seed 6, so slow drift of the laptop hits every condition equally. The function itself is a stdlib Python HTTP server (`function/app.py`) that hashes 64 KB per call and reports its own init time.

## Run (about 5 minutes)
Needs only Docker Desktop (running) and python3.
```bash
chmod +x run.sh
git init && git add . && git commit -m "Function, Dockerfile and benchmark script"
./run.sh                      # builds the image, runs 150 trials, writes results/ and logs/
git add -A && git commit -m "Benchmark run 1 (50 trials/condition)"
./run.sh                      # second full run, to check the numbers are stable
git add -A && git commit -m "Benchmark run 2 (repeatability)"
```
Outputs: `logs/run-*.log` (exact commands + full output), `results/<run-id>/summary.md` (tables), `trials.json` (every raw trial), `summary.json`.

## Files
- `function/app.py`, `function/Dockerfile`: the function
- `bench.py`: benchmark + analysis (stdlib only)
- `run.sh`: build + run + log
- `docs/REPORT.md`: the report
- `docs/NOTES_STUCK_AND_WEEK2.md`: where I got stuck and how I fixed it; week-2 plan
- `docs/AI_USE.md`: what AI tools were used for

## Runs in this repo
| run id | image | purpose |
|---|---|---|
| `20261103-160321` | original `python:3.12-slim` | run 1 |
| `20261103-160350` | original | run 2 (repeatability) |
| `20261103-160654` | + `RUN python -m compileall` (current Dockerfile) | `.pyc` experiment |

To reproduce runs 1 and 2, delete the `RUN python -m compileall ...` line from `function/Dockerfile` and run `./run.sh`.
