"""
Measure average hop count per packet, by mesh size, directly from the
randomised destinations baked into each generated test mesh.

For each requested grid size, this script regenerates the test mesh N
times (each generation re-samples destinations), parses the embedded
[INJECT] log strings for source/destination coordinates, computes
per-packet Manhattan distance, and averages across all packets and
all runs. Output is a small table suitable for pasting into the R3
results table or the plot_results.py AVG_HOPS dict.

Run from the repo root:
    python3 scripts/measure_avg_hops.py
    python3 scripts/measure_avg_hops.py --grids 3x3 4x4 8x8 8x10 --runs 10

The script does not invoke actsim --- the destinations are part of the
generator's output, so parsing the .act files alone suffices.
"""

import argparse
import os
import re
import subprocess
import sys

import yaml

INJECT_RE = re.compile(
    r"\[INJECT\] from \((\d+),(\d+)\) to \((\d+),(\d+)\)"
)


def grid_dims(label):
    """Return (W, H) from a string like '4x4' or '8x10'."""
    w, h = label.lower().split("x")
    return int(w), int(h)


def gen_act_path(label, prs_mode=False):
    w, h = grid_dims(label)
    suffix = f"{w}x{h}_prs" if prs_mode else f"{w}x{h}"
    return f"test/gen/test_mesh_gen_{suffix}.act"


def parse_inject_lines(act_path):
    """Return list of (src_x, src_y, dst_x, dst_y) tuples from the file."""
    hops = []
    with open(act_path) as f:
        for line in f:
            m = INJECT_RE.search(line)
            if m:
                sx, sy, dx, dy = map(int, m.groups())
                hops.append((sx, sy, dx, dy))
    return hops


def measure_grid(label, runs, packets, load):
    """Regenerate the mesh `runs` times and average Manhattan distance."""
    w, h = grid_dims(label)
    grid_spec = w if w == h else [w, h]

    with open("test/test_config.yaml") as f:
        cfg = yaml.safe_load(f)
    cfg["grid_size"] = list(grid_spec) if isinstance(grid_spec, list) else grid_spec
    cfg["experiment"]["packets_per_active_core"] = packets
    cfg["experiment"]["spatial_load_percent"] = load
    cfg["experiment"]["injection_delay_cycles"] = 0
    with open("test/test_config.yaml", "w") as f:
        yaml.dump(cfg, f)

    act_path = gen_act_path(label)
    per_run_means = []
    total_packets = 0
    for i in range(runs):
        subprocess.run(
            ["python3", "generate_act_mesh.py"],
            cwd="test", check=True, stdout=subprocess.DEVNULL,
        )
        pkts = parse_inject_lines(act_path)
        if not pkts:
            print(f"   run {i+1}: WARNING no packets parsed from {act_path}",
                  file=sys.stderr)
            continue
        dists = [abs(sx - dx) + abs(sy - dy) for sx, sy, dx, dy in pkts]
        per_run_means.append(sum(dists) / len(dists))
        total_packets += len(dists)

    if not per_run_means:
        return None, 0
    return sum(per_run_means) / len(per_run_means), total_packets


def main():
    parser = argparse.ArgumentParser(description="Measure avg hop count per grid.")
    parser.add_argument("--grids", nargs="+",
                        default=["3x3", "4x4", "8x8", "8x10"],
                        help="Mesh sizes to measure.")
    parser.add_argument("--runs", type=int, default=10,
                        help="Mesh regenerations per grid.")
    parser.add_argument("--packets", type=int, default=5,
                        help="packets_per_active_core during regeneration.")
    parser.add_argument("--load", type=int, default=100,
                        help="spatial_load_percent during regeneration.")
    args = parser.parse_args()

    print(f"Measuring avg hop count over {args.runs} regenerations per grid")
    print(f"(packets/core={args.packets}, load={args.load}%).\n")

    print(f"{'Grid':<6} | {'Runs':<5} | {'Pkts':<7} | {'Avg hops':<10}")
    print("-" * 40)
    for grid in args.grids:
        mean, total = measure_grid(grid, args.runs, args.packets, args.load)
        if mean is None:
            print(f"{grid:<6} | {args.runs:<5} | (no packets)")
        else:
            print(f"{grid:<6} | {args.runs:<5} | {total:<7} | {mean:>8.3f}")


if __name__ == "__main__":
    main()
