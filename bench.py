"""
Track D benchmark: cold vs frozen ("thawed") vs warm latency of a containerised
serverless-style function, on a laptop with Docker.

Three conditions, each measured as "time until the first successful response":

  cold   : nothing is running. Start a NEW container (docker run) and poll the function
           until it answers. This is a serverless cold start: create the sandbox, start the
           runtime, initialise the app, serve the request.
  thawed : the container exists but is FROZEN (docker pause = cgroup freezer, similar in
           spirit to how AWS Lambda freezes an execution environment between invocations).
           Unfreeze it (docker unpause) and send the request.
  warm   : the container is already running ("pre-warmed"). Just send the request.

Other measurements:
  - docker CLI overhead: time of a trivial `docker inspect` call, because cold and thawed
    trials include one docker CLI call each and that cost is not part of the "platform".
  - the app's own init time (reported by the function), to split a cold start.

Run order: all trials of all conditions are shuffled together with random seed 6
(last two digits of BITS ID f20231006), so slow drift of the machine (heat, background
apps) affects every condition equally instead of whichever ran last.

Usage:  python3 bench.py --trials 50
Writes: results/<run-id>/trials.json, summary.md, summary.json
"""

import argparse
import datetime
import http.client
import json
import os
import platform
import random
import statistics
import subprocess
import time
import urllib.error
import urllib.request

SEED = 6
IMAGE = "coldstart-fn:1.0"
COLD_PORT = 18090
THAW_PORT = 18091
WARM_PORT = 18092
POLL_INTERVAL_SECONDS = 0.005     # 5 ms polling -> cold-start resolution is about 5 ms
COLD_START_TIMEOUT_SECONDS = 30
CONDITIONS = ["cold", "thawed", "warm"]


def run_docker(arguments):
    """Run a docker CLI command; return (stdout, elapsed_ms). Raise if it fails."""
    start_time = time.perf_counter()
    completed = subprocess.run(["docker"] + arguments, capture_output=True, text=True)
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    if completed.returncode != 0:
        raise RuntimeError(f"docker {' '.join(arguments)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip(), elapsed_ms


def invoke(port, timeout_seconds=2.0):
    """Send one request to the function. Returns the parsed JSON body."""
    url = f"http://127.0.0.1:{port}/invoke"
    with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
        return json.loads(response.read())


def invoke_until_ready(port, start_time):
    """Poll until the function answers. Returns (body, number_of_attempts)."""
    attempts = 0
    while True:
        attempts += 1
        try:
            return invoke(port, timeout_seconds=1.0), attempts
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError, OSError, ValueError):
            # Not listening yet (connection refused/reset by Docker's port proxy, etc.)
            if time.perf_counter() - start_time > COLD_START_TIMEOUT_SECONDS:
                raise RuntimeError(f"function on port {port} did not become ready in time")
            time.sleep(POLL_INTERVAL_SECONDS)


def remove_container(name):
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True)


def cold_trial(trial_number):
    container_name = f"coldstart-cold-{trial_number}"
    remove_container(container_name)
    start_time = time.perf_counter()
    _, docker_run_ms = run_docker([
        "run", "-d", "--name", container_name,
        "-p", f"127.0.0.1:{COLD_PORT}:8080", IMAGE,
    ])
    body, attempts = invoke_until_ready(COLD_PORT, start_time)
    total_ms = (time.perf_counter() - start_time) * 1000
    remove_container(container_name)   # the next cold trial must start from nothing
    return {"total_ms": total_ms, "docker_cli_ms": docker_run_ms,
            "app_init_ms": body.get("init_ms"), "poll_attempts": attempts}


def thawed_trial():
    # Precondition: the thaw container is paused (frozen).
    start_time = time.perf_counter()
    _, docker_unpause_ms = run_docker(["unpause", "coldstart-thaw"])
    body, attempts = invoke_until_ready(THAW_PORT, start_time)
    total_ms = (time.perf_counter() - start_time) * 1000
    run_docker(["pause", "coldstart-thaw"])   # freeze again for the next thawed trial
    return {"total_ms": total_ms, "docker_cli_ms": docker_unpause_ms,
            "app_init_ms": body.get("init_ms"), "poll_attempts": attempts}


def warm_trial():
    start_time = time.perf_counter()
    invoke(WARM_PORT)
    total_ms = (time.perf_counter() - start_time) * 1000
    return {"total_ms": total_ms, "docker_cli_ms": 0.0, "app_init_ms": None, "poll_attempts": 1}


def percentile(sorted_values, percent):
    position = (len(sorted_values) - 1) * percent / 100.0
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    fraction = position - lower_index
    return sorted_values[lower_index] + (sorted_values[upper_index] - sorted_values[lower_index]) * fraction


def describe(values):
    sorted_values = sorted(values)
    return {
        "n": len(sorted_values),
        "mean": statistics.fmean(sorted_values),
        "stdev": statistics.stdev(sorted_values) if len(sorted_values) > 1 else 0.0,
        "min": sorted_values[0],
        "p50": percentile(sorted_values, 50),
        "p90": percentile(sorted_values, 90),
        "p95": percentile(sorted_values, 95),
        "max": sorted_values[-1],
    }


def bootstrap_median_difference(values_a, values_b, random_generator, resamples=2000):
    """95% CI for median(a) - median(b), resampling trials with replacement."""
    differences = []
    for _ in range(resamples):
        sample_a = random_generator.choices(values_a, k=len(values_a))
        sample_b = random_generator.choices(values_b, k=len(values_b))
        differences.append(statistics.median(sample_a) - statistics.median(sample_b))
    differences.sort()
    return percentile(differences, 2.5), percentile(differences, 97.5)


def environment_info():
    docker_version, _ = run_docker(["version", "--format", "{{.Server.Version}} ({{.Server.Os}}/{{.Server.Arch}})"])
    docker_resources, _ = run_docker(["info", "--format", "{{.NCPU}} CPUs, {{.MemTotal}} bytes RAM"])
    image_size, _ = run_docker(["image", "inspect", IMAGE, "--format", "{{.Size}}"])
    return {
        "host": f"{platform.system()} {platform.release()} {platform.machine()}",
        "python_on_host": platform.python_version(),
        "docker_server": docker_version,
        "docker_vm_resources": docker_resources,
        "image": IMAGE,
        "image_size_bytes": int(image_size),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=50, help="measured trials per condition")
    parser.add_argument("--warmup", type=int, default=3, help="unrecorded trials per condition first")
    arguments = parser.parse_args()

    run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    output_directory = os.path.join("results", run_id)
    os.makedirs(output_directory, exist_ok=True)

    print(f"run id {run_id}; {arguments.trials} trials per condition (+{arguments.warmup} warm-up); seed {SEED}")
    environment = environment_info()
    print("environment:", json.dumps(environment))

    # Set up the long-lived containers for the thawed and warm conditions.
    for name in ("coldstart-thaw", "coldstart-warm"):
        remove_container(name)
    run_docker(["run", "-d", "--name", "coldstart-thaw", "-p", f"127.0.0.1:{THAW_PORT}:8080", IMAGE])
    run_docker(["run", "-d", "--name", "coldstart-warm", "-p", f"127.0.0.1:{WARM_PORT}:8080", IMAGE])
    invoke_until_ready(THAW_PORT, time.perf_counter())
    invoke_until_ready(WARM_PORT, time.perf_counter())
    run_docker(["pause", "coldstart-thaw"])

    # Docker CLI overhead: a trivial command, timed.
    cli_overhead_ms = [run_docker(["inspect", "--format", "{{.State.Status}}", "coldstart-warm"])[1]
                       for _ in range(20)]

    # Warm-up (not recorded): the very first cold start after a build/boot also pays for
    # reading the image from disk; we record those separately as "first_cold_ms".
    first_cold_ms = []
    for warmup_number in range(arguments.warmup):
        first_cold_ms.append(cold_trial(f"warmup{warmup_number}")["total_ms"])
        thawed_trial()
        warm_trial()

    # Measured trials, all conditions shuffled together with seed 6.
    schedule = [condition for condition in CONDITIONS for _ in range(arguments.trials)]
    random.Random(SEED).shuffle(schedule)

    trials = []
    for index, condition in enumerate(schedule):
        if condition == "cold":
            result = cold_trial(index)
        elif condition == "thawed":
            result = thawed_trial()
        else:
            result = warm_trial()
        result.update({"index": index, "condition": condition})
        trials.append(result)
        if (index + 1) % 15 == 0:
            print(f"  {index + 1}/{len(schedule)} trials done")

    for name in ("coldstart-thaw", "coldstart-warm"):
        subprocess.run(["docker", "unpause", name], capture_output=True)
        remove_container(name)

    # ---------------- analysis ----------------
    by_condition = {condition: [trial["total_ms"] for trial in trials if trial["condition"] == condition]
                    for condition in CONDITIONS}
    stats = {condition: describe(values) for condition, values in by_condition.items()}
    cold_trials = [trial for trial in trials if trial["condition"] == "cold"]
    cold_breakdown = {
        "docker_run_cli_ms": describe([trial["docker_cli_ms"] for trial in cold_trials]),
        "app_init_ms": describe([trial["app_init_ms"] for trial in cold_trials]),
    }
    cli_stats = describe(cli_overhead_ms)

    random_generator = random.Random(SEED)
    comparisons = {}
    for slower, faster in (("cold", "warm"), ("thawed", "warm"), ("cold", "thawed")):
        low, high = bootstrap_median_difference(by_condition[slower], by_condition[faster], random_generator)
        comparisons[f"{slower}_minus_{faster}"] = {
            "median_difference_ms": stats[slower]["p50"] - stats[faster]["p50"],
            "ratio_of_medians": stats[slower]["p50"] / stats[faster]["p50"],
            "ci95_low_ms": low, "ci95_high_ms": high,
        }

    summary = {
        "run_id": run_id, "seed": SEED, "trials_per_condition": arguments.trials,
        "warmup_per_condition": arguments.warmup, "poll_interval_ms": POLL_INTERVAL_SECONDS * 1000,
        "environment": environment, "stats_ms": stats, "cold_breakdown": cold_breakdown,
        "docker_cli_overhead_ms": cli_stats, "first_cold_ms_warmup": first_cold_ms,
        "comparisons": comparisons,
    }
    with open(os.path.join(output_directory, "trials.json"), "w") as file_handle:
        json.dump({"schedule": schedule, "trials": trials, "cli_overhead_ms": cli_overhead_ms}, file_handle, indent=1)
    with open(os.path.join(output_directory, "summary.json"), "w") as file_handle:
        json.dump(summary, file_handle, indent=2)

    markdown = build_markdown(summary)
    with open(os.path.join(output_directory, "summary.md"), "w") as file_handle:
        file_handle.write(markdown)
    print(markdown)
    print(f"results written to {output_directory}")


def build_markdown(summary):
    lines = [f"# Cold-start benchmark summary (run {summary['run_id']})", ""]
    environment = summary["environment"]
    lines.append(f"- Host: {environment['host']}; Docker {environment['docker_server']}; VM: {environment['docker_vm_resources']}")
    lines.append(f"- Image {environment['image']}: {environment['image_size_bytes'] / 1e6:.1f} MB")
    lines.append(f"- {summary['trials_per_condition']} measured trials per condition "
                 f"(+{summary['warmup_per_condition']} warm-up each, discarded); order shuffled with seed {summary['seed']}")
    lines.append(f"- Polling interval {summary['poll_interval_ms']:.0f} ms (resolution of cold/thawed timings)")
    lines.append("")
    lines.append("## Time to first successful response (ms)")
    lines.append("")
    lines.append("| condition | n | mean | stdev | min | p50 | p90 | p95 | max |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for condition, row in summary["stats_ms"].items():
        lines.append(f"| {condition} | {row['n']} | {row['mean']:.1f} | {row['stdev']:.1f} | {row['min']:.1f} | "
                     f"{row['p50']:.1f} | {row['p90']:.1f} | {row['p95']:.1f} | {row['max']:.1f} |")
    lines.append("")
    lines.append("## Differences of medians, with 95% bootstrap CI (seed 6)")
    lines.append("")
    lines.append("| comparison | difference (ms) | ratio | 95% CI (ms) |")
    lines.append("|---|---|---|---|")
    for name, row in summary["comparisons"].items():
        lines.append(f"| {name} | {row['median_difference_ms']:+.1f} | {row['ratio_of_medians']:.1f}x | "
                     f"[{row['ci95_low_ms']:+.1f}, {row['ci95_high_ms']:+.1f}] |")
    lines.append("")
    breakdown = summary["cold_breakdown"]
    cli = summary["docker_cli_overhead_ms"]
    lines.append("## Where a cold start's time goes (medians, ms)")
    lines.append("")
    lines.append(f"- `docker run -d` command returned after: {breakdown['docker_run_cli_ms']['p50']:.1f} "
                 f"(of which plain docker CLI overhead, from a trivial `docker inspect`: {cli['p50']:.1f})")
    lines.append(f"- Python app init inside the container (imports + bind socket): {breakdown['app_init_ms']['p50']:.1f}")
    lines.append(f"- From `docker run` returning to the first response (Python start-up + the app init above "
                 f"+ port publishing + up to one poll interval): "
                 f"{summary['stats_ms']['cold']['p50'] - breakdown['docker_run_cli_ms']['p50']:.1f}")
    first = ", ".join(f"{value:.0f}" for value in summary["first_cold_ms_warmup"])
    lines.append(f"- First cold starts of the session (warm-up, not in the table): {first}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
