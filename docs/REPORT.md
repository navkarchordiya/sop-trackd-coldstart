# Cold Start vs Pre-warmed Latency of a Containerised Serverless-style Function

**Track D (Cloud, serverless and microservices performance) · Navkar Chordiya, ID 2023B3A71006P · Random seed: 6** (last two digits of my ID; used to shuffle trial order and in the bootstrap) · Repository: [github.com/navkarchordiya/sop-trackd-coldstart](https://github.com/navkarchordiya/sop-trackd-coldstart)

A cold start of my containerised function took **237 ms** at the median, compared with **1.4 ms** for a pre-warmed instance and **28 ms** for a frozen-then-thawed one. Most of the cold start was Python recompiling its standard library. Precompiling it in the image **halved the cold start to 123 ms** and left warm and thawed latency unchanged.

## 1. Goal
Measure how much a cold start costs a serverless-style function, compared with a pre-warmed instance and with a frozen-then-thawed instance. Then find out which part of the cold start dominates, and whether it can be reduced.

## 2. Method
**Setup.** Apple Silicon Mac (arm64), Docker Desktop with Docker Engine 28.3.2 (8 CPUs, 4 GB RAM for the Docker VM). The function is a ~50-line Python standard-library HTTP server on `python:3.12-slim` (43.6 MB image). Each call hashes 64 KB and returns JSON. The function also reports its own initialisation time.

**Three conditions**, each timed from the start of the action to the first successful response:
- **Cold:** nothing running. `docker run` a new container, then poll every 5 ms until it answers.
- **Thawed:** the container exists but is frozen with `docker pause` (cgroup freezer, similar in spirit to Lambda freezing idle environments). Timed from `docker unpause` to the response.
- **Warm (pre-warmed):** the container is already running; one request.

**Runs.** 50 measured trials per condition (150 per run), after 3 discarded warm-up trials each. All 150 trials are shuffled together with seed 6, so slow drift of the laptop (heat, background apps) hits every condition equally rather than whichever runs last. Two identical runs check repeatability, then one run uses a modified image (§4). I report medians and tail percentiles, plus a 95% bootstrap CI (2,000 resamples, seed 6) for differences of medians. I also timed a trivial `docker inspect` to estimate the Docker CLI's own overhead (14.5 ms), which is included in the cold and thawed timings.

## 3. Results
Cold starts cost about 235 ms more than a warm call, and the two runs agree to within 2 ms at the median.

| Condition | Run 1 p50 (ms) | Run 1 p95 (ms) | Run 1 max (ms) | Run 2 p50 (ms) | Run 2 p95 (ms) | Run 2 max (ms) |
|---|---|---|---|---|---|---|
| Cold | 237.0 | 250.7 | 334.5 | 236.6 | 250.1 | 262.1 |
| Thawed | 29.6 | 41.0 | 60.6 | 27.9 | 32.0 | 32.6 |
| Warm | 1.4 | 3.2 | 3.5 | 1.4 | 2.3 | 2.7 |

- **Cold minus warm:** +235.5 ms at the median (about 164x), 95% CI [+233.2, +238.7] ms in run 1; +235.2 ms in run 2.
- **Thawed minus warm:** +28.1 ms (CI [+25.4, +29.0]). Unfreezing costs about one-eighth of a cold start, so keeping an environment frozen rather than destroyed recovers most of the benefit of pre-warming.
- **Where a cold start goes (medians, run 1):** `docker run` returned after 109 ms, of which about 15 ms is plain CLI overhead. The function's own initialisation (imports and binding the socket) took **124 ms**, close to the entire 128 ms between `docker run` returning and the first response. App start-up, not the container platform, was the largest single cost.
- The first cold starts of the session (warm-up, excluded) took 222–257 ms, barely above later ones, because the 43.6 MB image was already on local disk.

Run ids: `20261103-160321` (run 1), `20261103-160350` (run 2), `20261103-160654` (experiment).

## 4. Experiment: finding and removing the main cost
Precompiling Python's standard library into the image cut the median cold start from 237 ms to 123 ms (−48%).

**Hypothesis.** 124 ms of initialisation is far too long for a program that only imports a few standard-library modules. The official `python` images strip compiled `.pyc` files to save space, so each brand-new container must compile the modules it imports from source on first use, and that happens only on a cold start.

**Test.** I added one line to the Dockerfile, `RUN python -m compileall -q /usr/local/lib/python3.12`, rebuilt, and reran the identical benchmark (50 trials per condition, seed 6).

| Image | Cold p50 (ms) | App init p50 (ms) | Thawed p50 (ms) | Warm p50 (ms) | Image size (MB) |
|---|---|---|---|---|---|
| Original (runs 1 and 2) | 237 | 124 | 28–30 | 1.4 | 43.6 |
| Precompiled `.pyc` | 123 | 19 | 28 | 1.6 | 50.5 |

**Result.** App initialisation fell from 124 ms to 19 ms. Thawed and warm latency did not change, which acts as a control: only code that runs at start-up was affected, as the hypothesis predicts. The cost is 7 MB more image and 1.3 s more build time. With the fix, a cold start is mostly `docker run` itself (about 107 ms).

## 5. Limitations
**Main limitation: this is Docker on a laptop, not a real serverless platform.** An AWS Lambda cold start also includes placing the function on a host, booting a Firecracker microVM, and downloading the code or image. Here the image is already on local disk and, after the first trials, in memory. So my "cold" is really "container-cold, host-warm", and the absolute numbers are not Lambda numbers. The relative findings (cold vs thawed vs warm, and start-up compilation as a fixable cost) are what should carry over.

Other limits:
- **Resolution:** polling every 5 ms means cold and thawed times are only accurate to about 5 ms.
- **Overheads in every timing:** all timings include Docker Desktop's port forwarding, and cold and thawed include the Docker CLI (about 15 ms). These are the same for all conditions but inflate the absolute values.
- **Overlapping timers:** the app's init timer starts before `docker run` returns, so the parts of the cold-start breakdown overlap slightly and do not add up exactly (e.g. 19.4 ms of init vs 16.2 ms after `docker run`).
- **Sample size:** n = 50 per condition gives stable medians but only rough p95 and max values.
- **A tiny function:** real functions with heavy imports (pandas, an ML model) would spend far longer in initialisation.

## 6. Use of AI tools
See [AI_USE.md](AI_USE.md).
