import subprocess
import yaml
import re
import os

# =====================================================================
# EXPERIMENT PARAMETERS (Feel free to change these!)
# =====================================================================
grid_sizes = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]                    # e.g., 2x2, 3x3
packets_per_core_list = [1, 3, 5]      # Burst vs Sustained traffic
load_percents = [10, 25, 50, 75, 100]      # 10% to 100% spatial load
runs_per_config = 10                   # Averages out the random traffic/delays

yaml_path = "test/test_config.yaml"

# Ensure the 'exp_outputs' folder exists inside the 'scripts' directory
os.makedirs("scripts/exp_outputs", exist_ok=True)

# Point the output file specifically to that new folder
output_file = "scripts/exp_outputs/simulation_results.txt"

# Initialize the text file with a clean header
with open(output_file, "w") as f:
    f.write("=== NoC Performance Results ===\n")
    f.write(f"Averaged over {runs_per_config} runs per configuration.\n")
    f.write("-" * 85 + "\n")
    f.write(f"{'Grid':<8} | {'Packets/Core':<14} | {'Load %':<8} | {'Avg Total Cycles':<18} | {'Avg Packet Latency':<20}\n")
    f.write("-" * 85 + "\n")

print("Starting Master Simulation Suite...")

# =====================================================================
# THE NESTED EXPERIMENT LOOPS
# =====================================================================
for grid in grid_sizes:
    for packets in packets_per_core_list:
        
        # Tracker: Remembers the actual physical core counts we have tested for this grid/packet combo
        tested_core_counts = set()
        
        # sorted(set()) removes direct duplicates (e.g. if you typed 50, 50)
        for load in sorted(set(load_percents)):
            
            # --- THE INDIRECT DUPLICATE CHECKER ---
            total_cores = grid * grid
            active_cores = max(1, int(((load / 100.0) * total_cores) + 0.5))
            
            if active_cores in tested_core_counts:
                print(f"\n⏭️  Skipping {load}% Load on {grid}x{grid} (Already tested {active_cores} physical cores)")
                continue # Jumps to the next percentage without running the simulation
                
            # If it is a new core count, add it to our tracker so we don't run it again
            tested_core_counts.add(active_cores)
            # --------------------------------------

            print(f"\n⚙️  Testing: {grid}x{grid} Grid | {packets} Pkts/Core | {load}% Load ({active_cores}/{total_cores} Cores awake)")
            
            # Store metrics for the 10 runs to average later
            run_total_times = []
            run_avg_latencies = []
            
            # 1. Update the YAML file for this specific config
            with open(yaml_path, "r") as f:
                cfg = yaml.safe_load(f)
                
            cfg["grid_size"] = grid
            cfg["experiment"]["packets_per_active_core"] = packets
            cfg["experiment"]["spatial_load_percent"] = load
            
            with open(yaml_path, "w") as f:
                yaml.dump(cfg, f)

            # 2. Run the iterations to get an average
            for i in range(runs_per_config):
                print(f"   -> Run {i+1}/{runs_per_config}... ", end="", flush=True)
                
                # Generate the new mesh (runs inside 'test' folder)
                subprocess.run(
                    ["python3", "generate_act_mesh.py"], 
                    cwd="test", 
                    check=True, 
                    stdout=subprocess.DEVNULL
                )
                
                # Run actsim and catch the output
                process = subprocess.run(
                    ["actsim", "-Wlang_subst:off", "test/gen/test_mesh_gen.act", "test_mesh"],
                    input="cycle\nquit\n", 
                    text=True, 
                    capture_output=True
                )
                
                output_text = process.stdout
                
                # 3. Parse the output! 
                timestamps = re.findall(r'\[\s*(\d+)\s*\]\s*<.*?>\s*\[EJECT\]', output_text)
                
                if timestamps:
                    ejection_times = [int(t) for t in timestamps]
                    
                    total_time = ejection_times[-1] 
                    avg_pkt_latency = sum(ejection_times) / len(ejection_times)
                    
                    run_total_times.append(total_time)
                    run_avg_latencies.append(avg_pkt_latency)
                    
                    print(f"Total: {total_time} | Avg Latency: {avg_pkt_latency:.1f}")
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
                    f.write(f"{grid}x{grid:<6} | {packets:<14} | {load:<8} | {avg_total_str:<18} | {avg_lat_str:<20}\n")

print(f"\n🎉 All testing complete! Data saved to {output_file}")