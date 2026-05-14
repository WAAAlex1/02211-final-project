import sys
import yaml
import random
import os
import argparse

def generate_act_mesh(config_file="test_config.yaml", output_file=None, prs_mode=False):
    if not os.path.exists("gen"):
        os.makedirs("gen")

    with open(config_file, "r") as f:
        cfg = yaml.safe_load(f)

    # --- SEPARATED PARAMETERS ---
    DATA_WIDTH = cfg["data_width"]

    # grid_size accepts either an int (square WxW) or a [W, H] list/tuple
    # (rectangular). Square form is the legacy default and kept for
    # backwards compatibility with the older config files.
    grid_spec = cfg["grid_size"]
    if isinstance(grid_spec, (list, tuple)):
        GRID_W, GRID_H = int(grid_spec[0]), int(grid_spec[1])
    else:
        GRID_W = GRID_H = int(grid_spec)

    # AUTOMATICALLY CALCULATE COORD_BITS AND PACKET SIZE.
    # COORD_BITS sizes the x_dest and y_dest fields, so it must hold the
    # larger of the two axes.
    max_coord = max(GRID_W - 1, GRID_H - 1)
    COORD_BITS = max(1, max_coord.bit_length())

    # The physical width of the entire channel
    PACKET_SIZE = (2 * COORD_BITS) + 2 + DATA_WIDTH

    PACKETS_PER_CORE = cfg["experiment"]["packets_per_active_core"]
    LOAD_PERCENT = cfg["experiment"]["spatial_load_percent"]
    # Optional inter-packet delay at each source (CHP-side counted loop iterations).
    # 0 = no delay (back-to-back at the max protocol-bounded rate, original behaviour).
    INJECTION_DELAY = int(cfg["experiment"].get("injection_delay_cycles", 0))

    # --- SPATIAL LOAD MATH ---
    total_cores = GRID_W * GRID_H
    raw_active = (LOAD_PERCENT / 100.0) * total_cores
    num_active_cores = max(1, round(raw_active))

    all_coords = [(x, y) for x in range(GRID_W) for y in range(GRID_H)]
    active_coords = set(random.sample(all_coords, num_active_cores))

    # Default output filename includes dimensions so square/rectangular
    # sweeps don't overwrite each other.
    if output_file is None:
        dims_tag = f"{GRID_W}x{GRID_H}"
        suffix = f"_{dims_tag}_prs" if prs_mode else f"_{dims_tag}"
        output_file = f"gen/test_mesh_gen{suffix}.act"

    # --- CHP-vs-PRS knobs ---
    # In PRS mode, NI<->router and inter-router wires are pkt_chan (ts_bd,
    # 2-phase wire-level), edge inputs need a null_source_prs to keep r/d
    # driven (no abstract chan to fall back on), and the test needs a
    # Reset pulse via the Initialize block.
    if prs_mode:
        router_type = "router_prs"
        ni_type = "network_interface_prs"
        sink_type = "route_sink_prs"
        sink_template_args = f"<{COORD_BITS}, {DATA_WIDTH}>"
        mesh_chan_type = f"pkt_chan<{COORD_BITS}, {DATA_WIDTH}>"
        imports = [
            'import "src/prs/router_prs.act";',
            'import "src/prs/network_interface_prs.act";',
            'import "src/prs/route_sink_prs.act";',
            'import "src/prs/null_source_prs.act";',
            'import globals;',
        ]
    else:
        router_type = "router"
        ni_type = "network_interface"
        sink_type = "route_sink"
        sink_template_args = f"<{COORD_BITS}, {DATA_WIDTH}>"
        mesh_chan_type = f"chan(int<{PACKET_SIZE}>)"
        imports = [
            'import "src/chp/router.act";',
            'import "src/chp/network_interface.act";',
            'import "src/chp/route_sink.act";',
        ]

    act = []

    # 1. Headers and Imports
    act.append(f"// Automatically generated {GRID_W}x{GRID_H} NoC Testbench ({'PRS' if prs_mode else 'CHP'} mode)")
    act.append(f"// Spatial Load: {LOAD_PERCENT}% ({num_active_cores}/{total_cores} Cores Active)")
    act.append(f"// Packets per Active Core: {PACKETS_PER_CORE}\n")
    for imp in imports:
        act.append(imp)
    act.append("")

    # 2. Mock core RX. core <-> NI is always abstract chan(int<W>) in both
    # modes (the NI's core_in/core_out are abstract chan in both flavours).
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

    # 3. GENERATE CORES (one mock_core_tx per (x,y) — active cores fire a
    # sequence of sends after their trigger arrives; inactive ones just
    # consume the trigger and stop).
    for y in range(GRID_H):
        for x in range(GRID_W):
            act.append(f"defproc mock_core_tx_{x}_{y} (chan?(int<1>) trigger; chan!(int<{PACKET_SIZE}>) out_chan) {{")
            act.append("    int<1> t;")
            # Declare the inter-packet delay counter only when we'll use it
            # (active core AND a non-zero injection_delay_cycles).
            if (x, y) in active_coords and INJECTION_DELAY > 0:
                act.append("    int<16> d;")

            if (x, y) in active_coords:
                # Build a list of CHP statements: trigger receive, then for each
                # packet an optional counted-loop delay (skipped on packet 0),
                # an [INJECT] log line, and the actual send. The log fires
                # immediately before the send, so its timestamp is the start of
                # the packet's end-to-end latency window.
                stmts = ["trigger?t"]
                for p in range(PACKETS_PER_CORE):
                    dest_x, dest_y = x, y
                    while (dest_x == x and dest_y == y):
                        dest_x = random.randint(0, GRID_W - 1)
                        dest_y = random.randint(0, GRID_H - 1)

                    payload = random.randint(1, 255)
                    packet_val = (dest_x << (COORD_BITS + 2 + DATA_WIDTH)) | (dest_y << (2 + DATA_WIDTH)) | payload

                    # Inject a counted-loop delay before all packets after the
                    # first, controlling the per-source inter-packet rate.
                    if p > 0 and INJECTION_DELAY > 0:
                        stmts.append("d := 0")
                        stmts.append(f"*[ d < {INJECTION_DELAY} -> d := d + 1 ]")

                    stmts.append(f'log(" [INJECT] from ({x},{y}) to ({dest_x},{dest_y}) payload={payload}")')
                    stmts.append(f'out_chan!{packet_val}')

                act.append("    chp {")
                for i, stmt in enumerate(stmts):
                    sep = ";" if i < len(stmts) - 1 else ""
                    act.append(f"        {stmt}{sep}")
                act.append("    }")

            else:
                act.append("    chp {")
                act.append("        trigger?t // Core is inactive, goes back to sleep (No semicolon)")
                act.append("    }")

            act.append("}\n")

    # 4. Generate Top Level Controller & Mesh Wiring
    act.append("defproc test_mesh () {")

    # Triggers and core-side channels (abstract chan in both modes).
    for y in range(GRID_H):
        for x in range(GRID_W):
            act.append(f"    chan(int<1>) t_{x}_{y};")
            act.append(f"    chan(int<{PACKET_SIZE}>) core_to_ni_{x}_{y}, ni_to_core_{x}_{y};")
    act.append("")

    # NI <-> router channels (CHP: abstract chan, PRS: pkt_chan).
    for y in range(GRID_H):
        for x in range(GRID_W):
            act.append(f"    {mesh_chan_type} ni_to_r_{x}_{y}, r_to_ni_{x}_{y};")
    act.append("")

    # Inter-router edges (CHP: chan, PRS: pkt_chan).
    # Horizontal (east-west) edges: GRID_W - 1 per row, GRID_H rows.
    for y in range(GRID_H):
        for x in range(GRID_W - 1):
            act.append(f"    {mesh_chan_type} e_{x}_{y}_to_{x+1}_{y}, w_{x+1}_{y}_to_{x}_{y};")
    # Vertical (north-south) edges: GRID_H - 1 per column, GRID_W columns.
    for x in range(GRID_W):
        for y in range(GRID_H - 1):
            act.append(f"    {mesh_chan_type} n_{x}_{y}_to_{x}_{y+1}, s_{x}_{y+1}_to_{x}_{y};")
    act.append("")

    # Edge wires (CHP: chan, PRS: pkt_chan).
    # Bottom edge (y=0): one S-direction stub per x in [0, GRID_W).
    # Top edge (y=GRID_H-1): one N-direction stub per x in [0, GRID_W).
    for i in range(GRID_W):
        act.append(f"    {mesh_chan_type} in_{i}_0_s, out_{i}_0_s; // Bottom Edge S")
        act.append(f"    {mesh_chan_type} in_{i}_{GRID_H-1}_n, out_{i}_{GRID_H-1}_n; // Top Edge N")
    # Left edge (x=0): one W-direction stub per y in [0, GRID_H).
    # Right edge (x=GRID_W-1): one E-direction stub per y in [0, GRID_H).
    for i in range(GRID_H):
        act.append(f"    {mesh_chan_type} in_0_{i}_w, out_0_{i}_w; // Left Edge W")
        act.append(f"    {mesh_chan_type} in_{GRID_W-1}_{i}_e, out_{GRID_W-1}_{i}_e; // Right Edge E")
    act.append("")

    # Instantiate cores, NIs, routers.
    for y in range(GRID_H):
        for x in range(GRID_W):
            act.append(f"    mock_core_tx_{x}_{y} core_tx_{x}_{y}(t_{x}_{y}, core_to_ni_{x}_{y});")
            act.append(f"    mock_core_rx<{x}, {y}> core_rx_{x}_{y}(ni_to_core_{x}_{y});")

            act.append(f"    {ni_type}<{COORD_BITS}, {DATA_WIDTH}, {x}, {y}> ni_{x}_{y}(core_to_ni_{x}_{y}, ni_to_r_{x}_{y}, r_to_ni_{x}_{y}, ni_to_core_{x}_{y});")

            in_E = f"w_{x+1}_{y}_to_{x}_{y}" if x < GRID_W - 1 else f"in_{x}_{y}_e"
            in_W = f"e_{x-1}_{y}_to_{x}_{y}" if x > 0 else f"in_{x}_{y}_w"
            in_N = f"s_{x}_{y+1}_to_{x}_{y}" if y < GRID_H - 1 else f"in_{x}_{y}_n"
            in_S = f"n_{x}_{y-1}_to_{x}_{y}" if y > 0 else f"in_{x}_{y}_s"

            out_E = f"e_{x}_{y}_to_{x+1}_{y}" if x < GRID_W - 1 else f"out_{x}_{y}_e"
            out_W = f"w_{x}_{y}_to_{x-1}_{y}" if x > 0 else f"out_{x}_{y}_w"
            out_N = f"n_{x}_{y}_to_{x}_{y+1}" if y < GRID_H - 1 else f"out_{x}_{y}_n"
            out_S = f"s_{x}_{y}_to_{x}_{y-1}" if y > 0 else f"out_{x}_{y}_s"

            # router_prs port order:  input_N, input_S, input_E, input_W, input_L,
            #                         output_N, output_S, output_E, output_W, output_L
            # The CHP router uses pos_x/neg_x/pos_y/neg_y naming. Same wiring,
            # different argument names — both take 10 ports in the same order
            # so we just pass positionally.
            act.append(f"    {router_type}<{COORD_BITS}, {DATA_WIDTH}, {x}, {y}> r_{x}_{y}(")
            if prs_mode:
                # PRS router: N, S, E, W, L
                act.append(f"        {in_N}, {in_S}, {in_E}, {in_W}, ni_to_r_{x}_{y},")
                act.append(f"        {out_N}, {out_S}, {out_E}, {out_W}, r_to_ni_{x}_{y}")
            else:
                # CHP router: pos_x (E), neg_x (W), pos_y (N), neg_y (S), local
                act.append(f"        {in_E}, {in_W}, {in_N}, {in_S}, ni_to_r_{x}_{y},")
                act.append(f"        {out_E}, {out_W}, {out_N}, {out_S}, r_to_ni_{x}_{y}")
            act.append("    );")
            act.append("")

    # Edge sinks (consume mesh-boundary outputs).
    # S/N sinks live along the bottom/top rows: one per column, x in [0, GRID_W).
    for i in range(GRID_W):
        act.append(f"    {sink_type}{sink_template_args} sk_s_{i}(out_{i}_0_s);")
        act.append(f"    {sink_type}{sink_template_args} sk_n_{i}(out_{i}_{GRID_H-1}_n);")
    # W/E sinks live along the left/right columns: one per row, y in [0, GRID_H).
    for i in range(GRID_H):
        act.append(f"    {sink_type}{sink_template_args} sk_w_{i}(out_0_{i}_w);")
        act.append(f"    {sink_type}{sink_template_args} sk_e_{i}(out_{GRID_W-1}_{i}_e);")
    act.append("")

    # Edge null sources (PRS only): drive r=0/d=0 on the mesh-boundary inputs.
    # In CHP mode, abstract chan() needs no driver — undriven means quiet.
    if prs_mode:
        for i in range(GRID_W):
            act.append(f"    null_source_prs{sink_template_args} ns_s_{i}(in_{i}_0_s);")
            act.append(f"    null_source_prs{sink_template_args} ns_n_{i}(in_{i}_{GRID_H-1}_n);")
        for i in range(GRID_H):
            act.append(f"    null_source_prs{sink_template_args} ns_w_{i}(in_0_{i}_w);")
            act.append(f"    null_source_prs{sink_template_args} ns_e_{i}(in_{GRID_W-1}_{i}_e);")
        act.append("")

    # Controller: fire every trigger in parallel.
    act.append("    chp {")
    act.append('        log("--- STARTING MESH SIMULATION ---");')

    triggers = [f"t_{x}_{y}!1" for y in range(GRID_H) for x in range(GRID_W)]
    for i, trig in enumerate(triggers):
        if i == len(triggers) - 1:
            act.append(f"        {trig} // Last trigger (No comma)")
        else:
            act.append(f"        {trig},")

    act.append("    }")
    act.append("}")

    # PRS mode needs a Reset pulse so the ~Reset-gated rules start clean.
    if prs_mode:
        act.append("")
        act.append("Initialize {")
        act.append("    actions { Reset+ };")
        act.append("    actions { Reset- }")
        act.append("}")

    with open(output_file, "w") as f:
        f.write("\n".join(act))

    print(f"Generated {output_file} ({GRID_W}x{GRID_H} Mesh, {num_active_cores} Active Cores, {COORD_BITS} Coord Bits, {PACKET_SIZE}-bit packets, {'PRS' if prs_mode else 'CHP'} mode)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate ACT mesh testbench (CHP or PRS).")
    parser.add_argument("--prs", action="store_true",
                        help="Generate a 2-phase PRS mesh (uses src/prs/* modules and pkt_chan wires)")
    parser.add_argument("--config", default="test_config.yaml", help="Path to the YAML config")
    parser.add_argument("--output", default=None, help="Output .act path (default: gen/test_mesh_gen[_prs].act)")
    args = parser.parse_args()

    generate_act_mesh(config_file=args.config, output_file=args.output, prs_mode=args.prs)