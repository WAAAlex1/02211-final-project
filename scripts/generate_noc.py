import sys
import yaml


def is_edge_core(x, y, grid_size):
    return (
        x == 0 or
        y == 0 or
        x == grid_size - 1 or
        y == grid_size - 1
    )


def neighbor_coordinate(x, y, direction):

    if direction == "north":
        return x, y - 1

    elif direction == "south":
        return x, y + 1

    elif direction == "east":
        return x + 1, y

    elif direction == "west":
        return x - 1, y

    else:
        raise ValueError(
            f"Unknown direction '{direction}'"
        )


# Main Generator
def generate_noc_top(grid_size,
                     config_file="noc_config.yaml",
                     output_file="gen/noc_top.sv"):

    if grid_size < 2:
        raise ValueError(
            "Grid size must be >= 2"
        )

    # Load YAML configuration
    with open(config_file, "r") as f:
        cfg = yaml.safe_load(f)

    data_width = cfg["data_width"]

    core_cfg = cfg["core"]
    router_cfg = cfg["router"]

    core_module_name = core_cfg["module_name"]
    router_module_name = router_cfg["module_name"]

    mesh_ports = core_cfg["mesh_ports"]

    router_conn = core_cfg["router_connection"]

    core_router_input = router_conn["core_input"]
    core_router_output = router_conn["core_output"]

    router_input_port = router_cfg["router_input"]
    router_output_port = router_cfg["router_output"]

    sv = []

    # Module Header
    sv.append("module noc_top #(")
    sv.append(
        f"    parameter int DATA_WIDTH = {data_width}"
    )
    sv.append(") (")
    sv.append("    input logic clk,")
    sv.append("    input logic rst_n")
    sv.append(");")
    sv.append("")

    # Internal Signals
    sv.append("    // ========================================")
    sv.append("    // Internal Signals")
    sv.append("    // ========================================")
    sv.append("")

    for y in range(grid_size):
        for x in range(grid_size):

            for direction in mesh_ports.keys():

                sv.append(
                    f"    logic [DATA_WIDTH-1:0] "
                    f"core_{x}_{y}_{direction}_out;"
                )

            if is_edge_core(x, y, grid_size):

                sv.append(
                    f"    logic [DATA_WIDTH-1:0] "
                    f"core_{x}_{y}_to_router;"
                )

                sv.append(
                    f"    logic [DATA_WIDTH-1:0] "
                    f"router_{x}_{y}_to_core;"
                )

            sv.append("")

    # Core Instantiations
    sv.append("    // ========================================")
    sv.append("    // Core Instantiations")
    sv.append("    // ========================================")
    sv.append("")

    for y in range(grid_size):
        for x in range(grid_size):

            sv.append(
f"""    {core_module_name} #(
        .DATA_WIDTH(DATA_WIDTH),
        .CORE_X({x}),
        .CORE_Y({y})
    ) core_{x}_{y} (
        .clk(clk),
        .rst_n(rst_n),"""
            )

            directions = list(mesh_ports.items())

            for idx, (direction, port_cfg) in enumerate(directions):

                input_port = port_cfg["input"]
                output_port = port_cfg["output"]

                connected_direction = port_cfg["connects_to"]

                nx, ny = neighbor_coordinate(
                    x,
                    y,
                    direction
                )

                valid_neighbor = (
                    0 <= nx < grid_size and
                    0 <= ny < grid_size
                )

                if valid_neighbor:

                    input_signal = (
                        f"core_{nx}_{ny}_"
                        f"{connected_direction}_out"
                    )

                else:

                    input_signal = (
                        "{DATA_WIDTH{1'b0}}"
                    )

                output_signal = (
                    f"core_{x}_{y}_{direction}_out"
                )

                sv.append("")
                sv.append(
                    f"        .{input_port}"
                    f"({input_signal}),"
                )

                # Last port handling
                is_last_mesh_port = (
                    idx == len(directions) - 1
                )

                has_router = is_edge_core(
                    x,
                    y,
                    grid_size
                )

                if (
                    is_last_mesh_port and
                    not has_router
                ):

                    sv.append(
                        f"        .{output_port}"
                        f"({output_signal}),"
                    )

                else:

                    sv.append(
                        f"        .{output_port}"
                        f"({output_signal}),"
                    )

            # Router Connections
            sv.append("")

            if is_edge_core(x, y, grid_size):

                sv.append(
                    f"        .{core_router_input}"
                    f"(router_{x}_{y}_to_core),"
                )

                sv.append(
                    f"        .{core_router_output}"
                    f"(core_{x}_{y}_to_router)"
                )

            else:

                sv.append(
                    f"        .{core_router_input}"
                    f"({{DATA_WIDTH{{1'b0}}}}),"
                )

                sv.append(
                    f"        .{core_router_output}()"
                )

            sv.append("    );")
            sv.append("")

    # Router Instantiations
    sv.append("    // ========================================")
    sv.append("    // Router Instantiations")
    sv.append("    // ========================================")
    sv.append("")

    for y in range(grid_size):
        for x in range(grid_size):

            if is_edge_core(x, y, grid_size):

                sv.append(
f"""    {router_module_name} #(
        .DATA_WIDTH(DATA_WIDTH),
        .ROUTER_X({x}),
        .ROUTER_Y({y})
    ) router_{x}_{y} (
        .clk(clk),
        .rst_n(rst_n),

        .{router_input_port}
            (core_{x}_{y}_to_router),

        .{router_output_port}
            (router_{x}_{y}_to_core)
    );

"""
                )

    # Endmodule

    sv.append("endmodule")

    # Write File
    with open(output_file, "w") as f:
        f.write("\n".join(sv))

    print(
        f"Generated {output_file} "
        f"for a {grid_size}x{grid_size} NoC"
    )


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print("Usage:")
        print(
            "    python generate_noc.py "
            "<grid_size>"
        )

        sys.exit(1)

    grid_size = int(sys.argv[1])

    generate_noc_top(grid_size)

