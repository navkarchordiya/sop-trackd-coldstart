<!-- Edit so it is exactly true before submitting. -->
# Use of AI tools
I used **Claude (Anthropic)** to write the first version of the function, Dockerfile, `bench.py` and `run.sh`, and a draft outline of the report. While testing, Claude found the ~40 ms Nagle/delayed-ACK stall in Python's `http.server` and the need to shuffle trial order. I read and understood all the code, [FILL: what you changed yourself], ran every benchmark myself on my Mac, and wrote the report in my own words. All numbers come from my own runs (`logs/`, `results/`).
