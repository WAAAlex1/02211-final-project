import subprocess
import yaml
import re
import os
import argparse

# =====================================================================
# CLI ARGS
# =====================================================================
parser = argparse.ArgumentParser(description="Run NoC simulation sweep (CHP or PRS).")
parser.add_argument("--prs", action="store_true",
                    help="Run against the 2-phase PRS mesh (uses src/prs/* modules)")
args = parser.parse_args()
PRS_MODE = args.prs

# =====================================================================
# EXPERIMENT PARAMETERS (Feel free to change these!)
# =====================================================================
# grid_sizes accepts either an int (square WxW) or a [W, H] list (rectangular).
# The generator and the YAML config_file consume the same dual form.
grid_sizes = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, [8, 10]]
packets_per_core_list = [1, 3, 5]      # Burst vs Sustained traffic
load_percents = [10, 25, 50, 75, 100]      # 10% to 100% spatial load
runs_per_config = 10                   # Averages out the random traffic/delays

yaml_path = "test/test_config.yaml"

# Ensure the 'exp_outputs' folder exists inside the 'scripts' directory
os.makedirs("scripts/exp_outputs", exist_ok=True)

# Separate output file per mode so CHP and PRS sweeps don't clobber each other.
output_file = "scripts/exp_outputs/simulation_results_prs.txt" if PRS_MODE \
              else "scripts/exp_outputs/simulation_results.txt"

# Generator args. The output path is per-grid because the generator's
# filename now encodes the W×H dimensions.
gen_cmd = ["python3", "generate_act_mesh.py"]
if PRS_MODE:
    gen_cmd.append("--prs")

def grid_dims(g):
    """Return (W, H) for a grid spec that may be int (square) or [W,H]."""
    if isinstance(g, (list, tuple)):
        return int(g[0]), int(g[1])
    return int(g), int(g)

def gen_act_path(g):
    w, h = grid_dims(g)
    suffix = f"{w}x{h}_prs" if PRS_MODE else f"{w}x{h}"
    return f"test/gen/test_mesh_gen_{suffix}.act"

def grid_label(g):
    w, h = grid_dims(g)
    return f"{w}x{h}"

# Initialize the text file with a clean header
with open(output_file, "w") as f:
    mode_label = "PRS (2-phase, gate-level event count)" if PRS_MODE \
                 else "CHP (abstract sync, one event per ?/!)"
    f.write(f"=== NoC Performance Results [{mode_label}] ===\n")
    f.write(f"Averaged over {runs_per_config} runs per configuration.\n")
    f.write("# Latency = mean per-packet (t_eject - t_inject).\n")
    f.write("# t_inject is logged in mock_core_tx immediately before out_chan!val;\n")
    f.write("# t_eject  is logged in mock_core_rx after in_chan?pkt.\n")
    f.write("-" * 85 + "\n")
    f.write(f"{'Grid':<8} | {'Packets/Core':<14} | {'Load %':<8} | {'Avg Total Cycles':<18} | {'Avg E2E Latency':<20}\n")
    f.write("-" * 85 + "\n")

print(f"Starting Master Simulation Suite [{'PRS' if PRS_MODE else 'CHP'} mode]...")

# =====================================================================
# THE NESTED EXPERIMENT LOOPS
# =====================================================================
for grid in grid_sizes:
    for packets in packets_per_core_list:
        
        # Tracker: Remembers the actual physical core counts we have tested for this grid/packet combo
        tested_core_counts = set()
        
        # sorted(set()) removes direct duplicates (e.g. if you typed 50, 50)
        for load in sorted(set(load_percents)):

            gw, gh = grid_dims(grid)
            label = grid_label(grid)

            # --- THE INDIRECT DUPLICATE CHECKER ---
            total_cores = gw * gh
            active_cores = max(1, int(((load / 100.0) * total_cores) + 0.5))

            if active_cores in tested_core_counts:
                print(f"\n⏭️  Skipping {load}% Load on {label} (Already tested {active_cores} physical cores)")
                continue # Jumps to the next percentage without running the simulation

            # If it is a new core count, add it to our tracker so we don't run it again
            tested_core_counts.add(active_cores)
            # --------------------------------------

            print(f"\n⚙️  Testing: {label} Grid | {packets} Pkts/Core | {load}% Load ({active_cores}/{total_cores} Cores awake)")

            # Store metrics for the 10 runs to average later
            run_total_times = []
            run_avg_latencies = []

            # 1. Update the YAML file for this specific config. Rectangular
            # grids are passed as a [W, H] list; the generator handles both
            # forms.
            with open(yaml_path, "r") as f:
                cfg = yaml.safe_load(f)

            cfg["grid_size"] = list(grid) if isinstance(grid, (list, tuple)) else grid
            cfg["experiment"]["packets_per_active_core"] = packets
            cfg["experiment"]["spatial_load_percent"] = load

            with open(yaml_path, "w") as f:
                yaml.dump(cfg, f)

            # 2. Run the iterations to get an average
            for i in range(runs_per_config):
                print(f"   -> Run {i+1}/{runs_per_config}... ", end="", flush=True)

                # Generate the new mesh (runs inside 'test' folder)
                subprocess.run(
                    gen_cmd,
                    cwd="test",
                    check=True,
                    stdout=subprocess.DEVNULL
                )

                # Run actsim and catch the output
                process = subprocess.run(
                    ["actsim", "-Wlang_subst:off", gen_act_path(grid), "test_mesh"],
                    input="cycle\nquit\n",
                    text=True,
                    capture_output=True
                )
                
                output_text = process.stdout

                # 3. Parse the output.
                # Per-packet latency uses INJECT/EJECT pairs:
                #   latency_i = t_eject_i - t_inject_i
                # Average over all packets equals (sum(eject) - sum(inject)) / N,
                # so we don't need to pair specific packets — only ensure counts
                # match (no drops, no deadlocks).
                eject_ts  = [int(t) for t in re.findall(r'\[\s*(\d+)\s*\]\s*<.*?>\s*\[EJECT\]',  output_text)]
                inject_ts = [int(t) for t in re.findall(r'\[\s*(\d+)\s*\]\s*<.*?>\s*\[INJECT\]', output_text)]

                if eject_ts and inject_ts and len(eject_ts) == len(inject_ts):
                    total_time = eject_ts[-1]
                    avg_pkt_latency = (sum(eject_ts) - sum(inject_ts)) / len(eject_ts)

                    run_total_times.append(total_time)
                    run_avg_latencies.append(avg_pkt_latency)

                    print(f"Total: {total_time} | Avg Latency: {avg_pkt_latency:.1f}  ({len(eject_ts)} packets)")
                elif eject_ts and inject_ts:
                    print(f"WARNING: count mismatch — {len(inject_ts)} injected, {len(eject_ts)} ejected. Mesh stuck?")
                elif not inject_ts:
                    print("ERROR: No packets injected. Did the controller fire?")
                else:
                    print("ERROR: No packets ejected. Did the mesh deadlock?")

            # 4. Calculate Final Averages and write to text file
            if run_total_times and run_avg_latencies:
                final_avg_total = sum(run_total_times) / len(run_total_times)
                final_avg_latency = sum(run_avg_latencies) / len(run_avg_latencies)
                
                # Format to 2 decimal places
                avg_total_str = f"{final_avg_total:.2f}"
                avg_lat_str = f"{final_avg_latency:.2f}"
                
                print(f"✅ Config Result -> Total: {avg_total_str} | Latency: {avg_lat_str}")
                
                # Append to our text file dynamically
                with open(output_file, "a") as f:
                    f.write(f"{label:<8} | {packets:<14} | {load:<8} | {avg_total_str:<18} | {avg_lat_str:<20}\n")

print(f"\n🎉 All testing complete! Data saved to {output_file}")