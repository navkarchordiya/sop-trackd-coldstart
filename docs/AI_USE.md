# Use of AI tools

I used **Claude (Anthropic)** throughout this task:

- **Code:** Claude only wrote the 1st version of function (`function/app.py`).
- **Debugging during development:** while testing, Claude found a ~40 ms Nagle/delayed-ACK stall in Python's `http.server` (fixed with `TCP_NODELAY` and one buffered write per response), and proposed shuffling all trials together with seed 6 to avoid order effects.
- **The `.pyc` experiment:** after seeing my first results, Claude pointed out that 124 ms of app initialisation was suspicious and suggested the missing-`.pyc` hypothesis. I made the Dockerfile change, ran the experiment and checked that warm and thawed latency stayed the same as a control.

