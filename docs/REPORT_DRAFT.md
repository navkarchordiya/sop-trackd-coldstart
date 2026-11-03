<!-- DRAFT: rewrite in your own words. All [FILL] values come from YOUR results/<run-id>/summary.md. Max 2 pages. -->

# Cold start vs pre-warmed latency of a containerised serverless-style function
**Navkar Chordiya (f20231006). Track D. Random seed: 6** (last two digits of my ID; used to shuffle trial order and in the bootstrap). Repo: [FILL link]

## Goal
Measure how much a cold start costs for a serverless-style function, compared with a pre-warmed instance and with a frozen-then-thawed instance, and break the cold start into its parts.

## Method
- **Setup:** [FILL Mac model/chip/RAM], Docker Desktop [FILL version] with [FILL] CPUs / [FILL] GB. Image `python:3.12-slim` + a ~50-line stdlib HTTP function ([FILL] MB image).
- **Conditions:** *cold*: `docker run` a new container and poll every 5 ms until the first 200 response. *Thawed*: an existing container frozen with `docker pause` (cgroup freezer, similar in spirit to Lambda freezing idle environments), timed from `docker unpause` to the first response. *Warm*: request to an already-running container (pre-warmed).
- **Runs:** 50 measured trials per condition (150 total) after 3 discarded warm-up trials each; all trials shuffled together with seed 6 so slow drift of the laptop affects all conditions equally. Two full runs to check repeatability. I report medians and tail percentiles (p90/p95), plus a 95% bootstrap CI (seed 6) for differences of medians.
- I also timed a trivial `docker inspect` to estimate the Docker CLI's own overhead, which is included in the cold and thawed timings but isn't really "platform" cost.

## Results (run [FILL id]; run 2 in brackets)
| condition | p50 (ms) | p95 (ms) | max (ms) |
|---|---|---|---|
| cold | [FILL] | [FILL] | [FILL] |
| thawed | [FILL] | [FILL] | [FILL] |
| warm (pre-warmed) | [FILL] | [FILL] | [FILL] |

- Cold minus warm: [FILL] ms at the median ([FILL]x), 95% CI [FILL]. Thawed minus warm: [FILL] ms.
- Cold-start breakdown (medians): `docker run` returned after [FILL] ms (about [FILL] ms of which is plain CLI overhead); the app's own init took [FILL] ms; the rest, [FILL] ms, is Python start-up, port publishing and polling.
- The first cold starts of the session (warm-up) took [FILL] ms, versus [FILL] ms later. The very first start also pays for reading the image from disk.
- [FILL: 2–3 sentences in your own words. What dominates a cold start? Is pre-warming worth it? Did run 2 agree with run 1?]

## Main limitation
**This is Docker on a laptop, not a real serverless platform.** AWS Lambda cold starts also include scheduling onto a host, starting a Firecracker microVM, and downloading the code/image. Here the image is already local and, after the first trial, in the page cache. So my "cold" is really "container-cold, host-warm", and the absolute numbers are not Lambda numbers. Also: polling at 5 ms limits resolution to about 5 ms; timings include the Docker CLI and Docker Desktop's port-forwarding (the same for all conditions, but it inflates absolute values); n = 50 per condition gives stable medians but only rough p95/max; and the function is tiny (real functions with heavy imports have much longer app-init time).

## AI use
[FILL from docs/AI_USE.md]
