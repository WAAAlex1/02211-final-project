import sys
import yaml
import random
import os

def generate_act_mesh(config_file="test_config.yaml", output_file="gen/test_mesh_gen.act"):
    if not os.path.exists("gen"):
        os.makedirs("gen")

    with open(config_file, "r") as f:
        cfg = yaml.safe_load(f)

    # --- SEPARATED PARAMETERS ---
    DATA_WIDTH = cfg["data_width"]
    GRID_SIZE = cfg["grid_size"]     

    # AUTOMATICALLY CALCULATE COORD_BITS AND PACKET SIZE
    max_coord = GRID_SIZE - 1
    COORD_BITS = max(1, max_coord.bit_length())
    
    # The physical width of the entire channel
    PACKET_SIZE = (2 * COORD_BITS) + 2 + DATA_WIDTH

    PACKETS_PER_CORE = cfg["experiment"]["packets_per_active_core"]
    LOAD_PERCENT = cfg["experiment"]["spatial_load_percent"]

    # --- SPATIAL LOAD MATH ---
    total_cores = GRID_SIZE * GRID_SIZE
    raw_active = (LOAD_PERCENT / 100.0) * total_cores
    num_active_cores = max(1, round(raw_active))
    
    all_coords = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE)]
    active_coords = set(random.sample(all_coords, num_active_cores))

    act = []
    
    # 1. Headers and Imports
    act.append(f"// Automatically generated {GRID_SIZE}x{GRID_SIZE} NoC Testbench")
    act.append(f"// Spatial Load: {LOAD_PERCENT}% ({num_active_cores}/{total_cores} Cores Active)")
    act.append(f"// Packets per Active Core: {PACKETS_PER_CORE}\n")
    act.append('import "src/router.act";')
    act.append('import "src/network_interface.act";')
    act.append('import "src/route_sink.act";\n')

    # 2. Standard Templates (FIXED: Dynamic Packet Size)
    act.append(f"""template <pint PORT_X, PORT_Y>
defproc mock_core_rx (chan?(int<{PACKET_SIZE}>) in_chan) {{
    int<{PACKET_SIZE}> pkt;
    chp {{
        *[
            in_chan?pkt;
            log(" [EJECT] Core at (", PORT_X, ",", PORT_Y, ") received Payload: ", pkt{{{DATA_WIDTH-1}..0}})
        ]
    }}
}}\n""")

    # 3. GENERATE CORES (FIXED: Dynamic Packet Size)
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            act.append(f"defproc mock_core_tx_{x}_{y} (chan?(int<1>) trigger; chan!(int<{PACKET_SIZE}>) out_chan) {{")
            act.append("    int<1> t;")
            
            if (x, y) in active_coords:
                act.append("    chp {")
                act.append("        trigger?t; // Wake up from controller")
                
                for p in range(PACKETS_PER_CORE):
                    dest_x, dest_y = x, y
                    while (dest_x == x and dest_y == y):
                        dest_x = random.randint(0, GRID_SIZE - 1)
                        dest_y = random.randint(0, GRID_SIZE - 1)
                    
                    payload = random.randint(1, 255)
                    
                    packet_val = (dest_x << (COORD_BITS + 2 + DATA_WIDTH)) | (dest_y << (2 + DATA_WIDTH)) | payload
                    
                    act.append(f"        // Packet {p+1} to ({dest_x},{dest_y})")
                    if p == PACKETS_PER_CORE - 1:
                        act.append(f"        out_chan!{packet_val} // Last packet (No semicolon)")
                    else:
                        act.append(f"        out_chan!{packet_val};")
                act.append("    }")
                
            else:
                act.append("    chp {")
                act.append("        trigger?t // Core is inactive, goes back to sleep (No semicolon)")
                act.append("    }")
                
            act.append("}\n")

    # 4. Generate Top Level Controller & Mesh Wiring 
    act.append("defproc test_mesh () {")
    
    # Declare Triggers and NI Channels (FIXED: Dynamic Packet Size)
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            act.append(f"    chan(int<1>) t_{x}_{y};")
            act.append(f"    chan(int<{PACKET_SIZE}>) core_to_ni_{x}_{y}, ni_to_core_{x}_{y};")
            act.append(f"    chan(int<{PACKET_SIZE}>) ni_to_r_{x}_{y}, r_to_ni_{x}_{y};")
    act.append("")

    # Declare Internal Mesh Wires (FIXED: Dynamic Packet Size)
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE - 1):
            act.append(f"    chan(int<{PACKET_SIZE}>) e_{x}_{y}_to_{x+1}_{y}, w_{x+1}_{y}_to_{x}_{y};")
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE - 1):
            act.append(f"    chan(int<{PACKET_SIZE}>) n_{x}_{y}_to_{x}_{y+1}, s_{x}_{y+1}_to_{x}_{y};")
    act.append("")

    # Declare Edge Sink Wires (FIXED: Dynamic Packet Size)
    for i in range(GRID_SIZE):
        act.append(f"    chan(int<{PACKET_SIZE}>) in_{i}_0_s, out_{i}_0_s; // Bottom Edge S")
        act.append(f"    chan(int<{PACKET_SIZE}>) in_{i}_{GRID_SIZE-1}_n, out_{i}_{GRID_SIZE-1}_n; // Top Edge N")
        act.append(f"    chan(int<{PACKET_SIZE}>) in_0_{i}_w, out_0_{i}_w; // Left Edge W")
        act.append(f"    chan(int<{PACKET_SIZE}>) in_{GRID_SIZE-1}_{i}_e, out_{GRID_SIZE-1}_{i}_e; // Right Edge E")
    act.append("")

    # Instantiate Everything
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            act.append(f"    mock_core_tx_{x}_{y} core_tx_{x}_{y}(t_{x}_{y}, core_to_ni_{x}_{y});")
            act.append(f"    mock_core_rx<{x}, {y}> core_rx_{x}_{y}(ni_to_core_{x}_{y});")
            
            act.append(f"    network_interface<{COORD_BITS}, {DATA_WIDTH}, {x}, {y}> ni_{x}_{y}(core_to_ni_{x}_{y}, ni_to_r_{x}_{y}, r_to_ni_{x}_{y}, ni_to_core_{x}_{y});")
            
            in_E = f"w_{x+1}_{y}_to_{x}_{y}" if x < GRID_SIZE - 1 else f"in_{x}_{y}_e"
            in_W = f"e_{x-1}_{y}_to_{x}_{y}" if x > 0 else f"in_{x}_{y}_w"
            in_N = f"s_{x}_{y+1}_to_{x}_{y}" if y < GRID_SIZE - 1 else f"in_{x}_{y}_n"
            in_S = f"n_{x}_{y-1}_to_{x}_{y}" if y > 0 else f"in_{x}_{y}_s"
            
            out_E = f"e_{x}_{y}_to_{x+1}_{y}" if x < GRID_SIZE - 1 else f"out_{x}_{y}_e"
            out_W = f"w_{x}_{y}_to_{x-1}_{y}" if x > 0 else f"out_{x}_{y}_w"
            out_N = f"n_{x}_{y}_to_{x}_{y+1}" if y < GRID_SIZE - 1 else f"out_{x}_{y}_n"
            out_S = f"s_{x}_{y}_to_{x}_{y-1}" if y > 0 else f"out_{x}_{y}_s"

            act.append(f"    router<{COORD_BITS}, {DATA_WIDTH}, {x}, {y}> r_{x}_{y}(")
            act.append(f"        {in_E}, {in_W}, {in_N}, {in_S}, ni_to_r_{x}_{y},")
            act.append(f"        {out_E}, {out_W}, {out_N}, {out_S}, r_to_ni_{x}_{y}")
            act.append("    );")
            act.append("")

    # Edge Sinks 
    for i in range(GRID_SIZE):
        act.append(f"    route_sink<{COORD_BITS}, {DATA_WIDTH}> sk_s_{i}(out_{i}_0_s);")
        act.append(f"    route_sink<{COORD_BITS}, {DATA_WIDTH}> sk_n_{i}(out_{i}_{GRID_SIZE-1}_n);")
        act.append(f"    route_sink<{COORD_BITS}, {DATA_WIDTH}> sk_w_{i}(out_0_{i}_w);")
        act.append(f"    route_sink<{COORD_BITS}, {DATA_WIDTH}> sk_e_{i}(out_{GRID_SIZE-1}_{i}_e);")
    act.append("")

    # Controller Firing
    act.append("    chp {")
    act.append('        log("--- STARTING MESH SIMULATION ---");')
    
    triggers = []
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            triggers.append(f"t_{x}_{y}!1")
            
    for i, trig in enumerate(triggers):
        if i == len(triggers) - 1:
            act.append(f"        {trig} // Last trigger (No semicolon)")
        else:
            act.append(f"        {trig};")
            
    act.append("    }")
    act.append("}")

    with open(output_file, "w") as f:
        f.write("\n".join(act))
        
    print(f"Generated {output_file} ({GRID_SIZE}x{GRID_SIZE} Mesh, {num_active_cores} Active Cores, {COORD_BITS} Coord Bits, {PACKET_SIZE}-bit packets)")

if __name__ == "__main__":
    generate_act_mesh()