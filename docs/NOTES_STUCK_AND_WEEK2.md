<!-- Rewrite in your own words; keep only what actually happened. -->

# Where I got stuck and how I fixed it
[FILL: anything YOU hit on your Mac: Docker Desktop not running, a port already in use, a first run much slower than the rest, etc. What you saw → why → the fix.]

Found while building/testing the code (AI-assisted, see AI_USE.md):
- **Every request took ~40 ms longer than it should.** Python's `http.server` sends headers and body as two packets; Nagle's algorithm plus the client's delayed ACK stalls the second one ~40 ms. That would have made "warm" look ~40 ms slow and shrunk the cold/warm gap. Fixed with `TCP_NODELAY` and one buffered write per response.
- **Order effects.** Running all cold trials, then all warm ones, mixes the condition with time (the laptop heats up, caches fill). Fixed by shuffling all trials together with seed 6 and discarding warm-up trials.

# Week 2
[FILL: one paragraph in your own words. Candidates:]
Run the same design on real AWS Lambda: Python vs Node vs Java/SnapStart, zip vs container image, 128 MB vs 1024 MB memory, and an idle-gap sweep (1, 5, 15, 30, 60 min) to find when environments get recycled. Compare provisioned concurrency against a scheduled "ping every 5 minutes" pre-warming, including cost. Make the function realistic (e.g. heavy imports like pandas or an ML model) to see app-init dominate.
