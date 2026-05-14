"""
Temporal injection-rate sweep. Holds spatial load and packet count fixed,
varies the inter-packet delay at each source by setting
`experiment.injection_delay_cycles` in the YAML and re-running actsim.

Default sweep: 4x4 and 8x8 meshes, 100% spatial load, 5 packets/core,
delays [0, 10, 25, 50, 100, 200, 500, 1000] CHP iterations, 10 runs each.

Usage:
    python3 scripts/run_temporal_sweep.py          # CHP mode
    python3 scripts/run_temporal_sweep.py --prs    # PRS mode

Output (in scripts/exp_outputs/):
    temporal_results.txt        (CHP)
    temporal_results_prs.txt    (PRS)
"""

import argparse
import os
import re
import subprocess
import sys

import yaml

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Temporal injection-rate sweep.")
parser.add_argument("--prs", action="store_true",
                    help="Run against the 2-phase PRS mesh")
parser.add_argument("--grids", nargs="+", default=["4x4", "8x8"],
                    help='Mesh sizes to sweep (e.g. "4x4" "8x8")')
parser.add_argument("--delays", nargs="+", type=int,
                    default=[0, 10, 25, 50, 100, 200, 500, 1000],
                    help="injection_delay_cycles values to sweep")
parser.add_argument("--packets", type=int, default=5,
                    help="packets_per_active_core (fixed across the sweep)")
parser.add_argument("--load", type=int, default=100,
                    help="spatial_load_percent (fixed across the sweep)")
parser.add_argument("--runs", type=int, default=10,
                    help="runs per (grid, delay) configuration (averaged)")
args = parser.parse_args()
PRS_MODE = args.prs


# -----------------------------------------------------------------------------
# Paths and IO
# -----------------------------------------------------------------------------
yaml_path = "test/test_config.yaml"
os.makedirs("scripts/exp_outputs", exist_ok=True)
output_file = ("scripts/exp_outputs/temporal_results_prs.txt" if PRS_MODE
               else "scripts/exp_outputs/temporal_results.txt")

gen_cmd = ["python3", "generate_act_mesh.py"]
if PRS_MODE:
    gen_cmd.append("--prs")


def grid_dims(label):
    """Return (W, H) from a string like '4x4' or '8x10'."""
    w, h = label.lower().split("x")
    return int(w), int(h)


def gen_act_path(label):
    w, h = grid_dims(label)
    suffix = f"{w}x{h}_prs" if PRS_MODE else f"{w}x{h}"
    return f"test/gen/test_mesh_gen_{suffix}.act"


# -----------------------------------------------------------------------------
# Header / append banner
# -----------------------------------------------------------------------------
mode_label = "PRS (2-phase, gate-level event count)" if PRS_MODE \
             else "CHP (abstract sync, one event per ?/!)"

if os.path.exists(output_file):
    # Append mode: existing sweep was run, just add new rows with a banner so
    # they're visually separable. Don't rewrite the header.
    with open(output_file, "a") as f:
        f.write(f"# Appended sweep delays={args.delays} grids={args.grids} "
                f"runs={args.runs} packets={args.packets} load={args.load}%\n")
else:
    with open(output_file, "w") as f:
        f.write(f"=== NoC Temporal Injection-Rate Sweep [{mode_label}] ===\n")
        f.write(f"Averaged over {args.runs} runs per configuration.\n")
        f.write(f"Fixed: packets_per_active_core={args.packets}, spatial_load_percent={args.load}.\n")
        f.write("# delay = injection_delay_cycles (counted-loop iterations between successive packets at each source).\n")
        f.write("# Latency = mean per-packet (t_eject - t_inject).\n")
        f.write("-" * 85 + "\n")
        f.write(f"{'Grid':<8} | {'Delay':<6} | {'Avg Total Cycles':<18} | {'Avg E2E Latency':<20}\n")
        f.write("-" * 85 + "\n")


print(f"Starting Temporal Sweep [{'PRS' if PRS_MODE else 'CHP'} mode]")
print(f"  grids:   {args.grids}")
print(f"  delays:  {args.delays}")
print(f"  packets: {args.packets}")
print(f"  load:    {args.load}%")
print(f"  runs:    {args.runs}")
print()


# -----------------------------------------------------------------------------
# Main sweep
# -----------------------------------------------------------------------------
for grid_label in args.grids:
    W, H = grid_dims(grid_label)
    grid_spec = W if W == H else [W, H]
    act_path = gen_act_path(grid_label)

    for delay in args.delays:
        print(f"[run] {grid_label} | delay={delay}")

        # Write YAML for this (grid, delay) config
        with open(yaml_path) as f:
            cfg = yaml.safe_load(f)
        cfg["grid_size"] = list(grid_spec) if isinstance(grid_spec, list) else grid_spec
        cfg["experiment"]["packets_per_active_core"] = args.packets
        cfg["experiment"]["spatial_load_percent"] = args.load
        cfg["experiment"]["injection_delay_cycles"] = delay
        with open(yaml_path, "w") as f:
            yaml.dump(cfg, f)

        run_totals, run_lats = [], []
        for i in range(args.runs):
            print(f"   run {i+1}/{args.runs}... ", end="", flush=True)
            subprocess.run(gen_cmd, cwd="test", check=True, stdout=subprocess.DEVNULL)
            p = subprocess.run(
                ["actsim", "-Wlang_subst:off", act_path, "test_mesh"],
                input="cycle\nquit\n", text=True, capture_output=True,
            )
            out = p.stdout
            inj = [int(t) for t in re.findall(r'\[\s*(\d+)\s*\]\s*<.*?>\s*\[INJECT\]', out)]
            ej  = [int(t) for t in re.findall(r'\[\s*(\d+)\s*\]\s*<.*?>\s*\[EJECT\]',  out)]
            if ej and inj and len(ej) == len(inj):
                total = ej[-1]
                lat = (sum(ej) - sum(inj)) / len(ej)
                run_totals.append(total)
                run_lats.append(lat)
                print(f"total={total} lat={lat:.1f}")
            elif ej and inj:
                print(f"COUNT MISMATCH inj={len(inj)} ej={len(ej)} — skipped")
            else:
                print("NO PACKETS — skipped")

        if run_totals and run_lats:
            avg_t = sum(run_totals) / len(run_totals)
            avg_l = sum(run_lats) / len(run_lats)
            print(f"   ✓ {grid_label} | delay={delay} -> total {avg_t:.2f} | lat {avg_l:.2f}")
            with open(output_file, "a") as f:
                f.write(f"{grid_label:<8} | {delay:<6} | {avg_t:<18.2f} | {avg_l:<20.2f}\n")
        else:
            print(f"   ✗ {grid_label} | delay={delay} — no successful runs")

print(f"\nDone. Rows written to {output_file}.")
