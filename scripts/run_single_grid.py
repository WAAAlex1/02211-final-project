"""
One-off sweep runner for a single grid size, appending rows to the existing
results files instead of overwriting them. Used to fill in mesh sizes that
weren't part of the original `run_experiments.py` square sweep.

Usage:
    python3 scripts/run_single_grid.py 8 10            # rectangular 8x10, CHP
    python3 scripts/run_single_grid.py 8 10 --prs      # rectangular 8x10, PRS
    python3 scripts/run_single_grid.py 8               # square 8x8 (any mode)

Output is appended to scripts/exp_outputs/simulation_results[_prs].txt with
the same column layout as the main sweep.
"""

import subprocess
import yaml
import re
import os
import sys
import argparse

parser = argparse.ArgumentParser(description="Run sweep for a single grid spec.")
parser.add_argument("width", type=int, help="Grid width (x dimension)")
parser.add_argument("height", type=int, nargs="?", default=None,
                    help="Grid height (y dimension). Defaults to width (square).")
parser.add_argument("--prs", action="store_true", help="Run against PRS mesh")
parser.add_argument("--packets", nargs="+", type=int, default=[1, 3, 5],
                    help="packets_per_active_core values to sweep")
parser.add_argument("--loads", nargs="+", type=int, default=[10, 25, 50, 75, 100],
                    help="spatial_load_percent values to sweep")
parser.add_argument("--runs", type=int, default=10, help="runs per config (averaged)")
args = parser.parse_args()

W = args.width
H = args.height if args.height is not None else W
PRS_MODE = args.prs

yaml_path = "test/test_config.yaml"
os.makedirs("scripts/exp_outputs", exist_ok=True)
output_file = "scripts/exp_outputs/simulation_results_prs.txt" if PRS_MODE \
              else "scripts/exp_outputs/simulation_results.txt"

gen_cmd = ["python3", "generate_act_mesh.py"]
if PRS_MODE:
    gen_cmd.append("--prs")

grid_spec = [W, H] if W != H else W
label = f"{W}x{H}"
suffix = f"{W}x{H}_prs" if PRS_MODE else f"{W}x{H}"
gen_act_path = f"test/gen/test_mesh_gen_{suffix}.act"

print(f"Single-grid sweep [{'PRS' if PRS_MODE else 'CHP'} mode] for grid {label}")
print(f"  packets/core: {args.packets}")
print(f"  loads:         {args.loads}")
print(f"  runs/config:   {args.runs}")
print(f"  appending to:  {output_file}")
print()

if not os.path.exists(output_file):
    print(f"WARNING: {output_file} does not exist. Run the full sweep first or it'll start empty.")

# Header banner so the appended rows are visually separable from the main table.
with open(output_file, "a") as f:
    f.write(f"# Single-grid sweep for {label} appended {os.popen('date').read().strip()}\n")

total_cores = W * H

for packets in args.packets:
    # Reset the dup tracker per (grid, packets) outer iteration, matching the
    # original run_experiments.py semantics — dedup is only between loads
    # that resolve to the same active-core count within a single packets
    # value, not across packet counts.
    tested_core_counts = set()
    for load in sorted(set(args.loads)):
        active_cores = max(1, int(((load / 100.0) * total_cores) + 0.5))
        if active_cores in tested_core_counts:
            print(f"[skip] {label} | {packets} pkts | {load}% (dup {active_cores} cores)")
            continue
        tested_core_counts.add(active_cores)

        print(f"[run]  {label} | {packets} pkts | {load}% ({active_cores}/{total_cores} cores)")

        with open(yaml_path, "r") as f:
            cfg = yaml.safe_load(f)
        cfg["grid_size"] = list(grid_spec) if isinstance(grid_spec, list) else grid_spec
        cfg["experiment"]["packets_per_active_core"] = packets
        cfg["experiment"]["spatial_load_percent"] = load
        with open(yaml_path, "w") as f:
            yaml.dump(cfg, f)

        run_total_times, run_avg_latencies = [], []
        for i in range(args.runs):
            print(f"   run {i+1}/{args.runs}... ", end="", flush=True)
            subprocess.run(gen_cmd, cwd="test", check=True, stdout=subprocess.DEVNULL)
            p = subprocess.run(
                ["actsim", "-Wlang_subst:off", gen_act_path, "test_mesh"],
                input="cycle\nquit\n",
                text=True,
                capture_output=True,
            )
            out = p.stdout
            inj_ts = [int(t) for t in re.findall(r'\[\s*(\d+)\s*\]\s*<.*?>\s*\[INJECT\]', out)]
            ej_ts  = [int(t) for t in re.findall(r'\[\s*(\d+)\s*\]\s*<.*?>\s*\[EJECT\]',  out)]
            if ej_ts and inj_ts and len(ej_ts) == len(inj_ts):
                total = ej_ts[-1]
                lat = (sum(ej_ts) - sum(inj_ts)) / len(ej_ts)
                run_total_times.append(total)
                run_avg_latencies.append(lat)
                print(f"total={total} lat={lat:.1f} ({len(ej_ts)} pkts)")
            elif ej_ts and inj_ts:
                print(f"COUNT MISMATCH inj={len(inj_ts)} ej={len(ej_ts)} — skipped")
            else:
                print("NO PACKETS — skipped")

        if run_total_times and run_avg_latencies:
            avg_total = sum(run_total_times) / len(run_total_times)
            avg_lat   = sum(run_avg_latencies) / len(run_avg_latencies)
            avg_total_str = f"{avg_total:.2f}"
            avg_lat_str   = f"{avg_lat:.2f}"
            print(f"   ✓ {label} | {packets} | {load}% -> total {avg_total_str} | lat {avg_lat_str}")
            with open(output_file, "a") as f:
                f.write(f"{label:<8} | {packets:<14} | {load:<8} | {avg_total_str:<18} | {avg_lat_str:<20}\n")

print(f"\nDone. Rows appended to {output_file}.")