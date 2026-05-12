module noc_top #(
    parameter int DATA_WIDTH = 32
) (
    input logic clk,
    input logic rst_n
);

    // ========================================
    // Internal Signals
    // ========================================

    logic [DATA_WIDTH-1:0] core_0_0_north_out;
    logic [DATA_WIDTH-1:0] core_0_0_south_out;
    logic [DATA_WIDTH-1:0] core_0_0_east_out;
    logic [DATA_WIDTH-1:0] core_0_0_west_out;
    logic [DATA_WIDTH-1:0] core_0_0_to_router;
    logic [DATA_WIDTH-1:0] router_0_0_to_core;

    logic [DATA_WIDTH-1:0] core_1_0_north_out;
    logic [DATA_WIDTH-1:0] core_1_0_south_out;
    logic [DATA_WIDTH-1:0] core_1_0_east_out;
    logic [DATA_WIDTH-1:0] core_1_0_west_out;
    logic [DATA_WIDTH-1:0] core_1_0_to_router;
    logic [DATA_WIDTH-1:0] router_1_0_to_core;

    logic [DATA_WIDTH-1:0] core_2_0_north_out;
    logic [DATA_WIDTH-1:0] core_2_0_south_out;
    logic [DATA_WIDTH-1:0] core_2_0_east_out;
    logic [DATA_WIDTH-1:0] core_2_0_west_out;
    logic [DATA_WIDTH-1:0] core_2_0_to_router;
    logic [DATA_WIDTH-1:0] router_2_0_to_core;

    logic [DATA_WIDTH-1:0] core_0_1_north_out;
    logic [DATA_WIDTH-1:0] core_0_1_south_out;
    logic [DATA_WIDTH-1:0] core_0_1_east_out;
    logic [DATA_WIDTH-1:0] core_0_1_west_out;
    logic [DATA_WIDTH-1:0] core_0_1_to_router;
    logic [DATA_WIDTH-1:0] router_0_1_to_core;

    logic [DATA_WIDTH-1:0] core_1_1_north_out;
    logic [DATA_WIDTH-1:0] core_1_1_south_out;
    logic [DATA_WIDTH-1:0] core_1_1_east_out;
    logic [DATA_WIDTH-1:0] core_1_1_west_out;

    logic [DATA_WIDTH-1:0] core_2_1_north_out;
    logic [DATA_WIDTH-1:0] core_2_1_south_out;
    logic [DATA_WIDTH-1:0] core_2_1_east_out;
    logic [DATA_WIDTH-1:0] core_2_1_west_out;
    logic [DATA_WIDTH-1:0] core_2_1_to_router;
    logic [DATA_WIDTH-1:0] router_2_1_to_core;

    logic [DATA_WIDTH-1:0] core_0_2_north_out;
    logic [DATA_WIDTH-1:0] core_0_2_south_out;
    logic [DATA_WIDTH-1:0] core_0_2_east_out;
    logic [DATA_WIDTH-1:0] core_0_2_west_out;
    logic [DATA_WIDTH-1:0] core_0_2_to_router;
    logic [DATA_WIDTH-1:0] router_0_2_to_core;

    logic [DATA_WIDTH-1:0] core_1_2_north_out;
    logic [DATA_WIDTH-1:0] core_1_2_south_out;
    logic [DATA_WIDTH-1:0] core_1_2_east_out;
    logic [DATA_WIDTH-1:0] core_1_2_west_out;
    logic [DATA_WIDTH-1:0] core_1_2_to_router;
    logic [DATA_WIDTH-1:0] router_1_2_to_core;

    logic [DATA_WIDTH-1:0] core_2_2_north_out;
    logic [DATA_WIDTH-1:0] core_2_2_south_out;
    logic [DATA_WIDTH-1:0] core_2_2_east_out;
    logic [DATA_WIDTH-1:0] core_2_2_west_out;
    logic [DATA_WIDTH-1:0] core_2_2_to_router;
    logic [DATA_WIDTH-1:0] router_2_2_to_core;

    // ========================================
    // Core Instantiations
    // ========================================

    core_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .CORE_X(0),
        .CORE_Y(0)
    ) core_0_0 (
        .clk(clk),
        .rst_n(rst_n),

        .north_data_in({DATA_WIDTH{1'b0}}),
        .north_data_out(core_0_0_north_out),

        .south_data_in(core_0_1_north_out),
        .south_data_out(core_0_0_south_out),

        .east_data_in(core_1_0_west_out),
        .east_data_out(core_0_0_east_out),

        .west_data_in({DATA_WIDTH{1'b0}}),
        .west_data_out(core_0_0_west_out),

        .router_in(router_0_0_to_core),
        .router_out(core_0_0_to_router)
    );

    core_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .CORE_X(1),
        .CORE_Y(0)
    ) core_1_0 (
        .clk(clk),
        .rst_n(rst_n),

        .north_data_in({DATA_WIDTH{1'b0}}),
        .north_data_out(core_1_0_north_out),

        .south_data_in(core_1_1_north_out),
        .south_data_out(core_1_0_south_out),

        .east_data_in(core_2_0_west_out),
        .east_data_out(core_1_0_east_out),

        .west_data_in(core_0_0_east_out),
        .west_data_out(core_1_0_west_out),

        .router_in(router_1_0_to_core),
        .router_out(core_1_0_to_router)
    );

    core_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .CORE_X(2),
        .CORE_Y(0)
    ) core_2_0 (
        .clk(clk),
        .rst_n(rst_n),

        .north_data_in({DATA_WIDTH{1'b0}}),
        .north_data_out(core_2_0_north_out),

        .south_data_in(core_2_1_north_out),
        .south_data_out(core_2_0_south_out),

        .east_data_in({DATA_WIDTH{1'b0}}),
        .east_data_out(core_2_0_east_out),

        .west_data_in(core_1_0_east_out),
        .west_data_out(core_2_0_west_out),

        .router_in(router_2_0_to_core),
        .router_out(core_2_0_to_router)
    );

    core_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .CORE_X(0),
        .CORE_Y(1)
    ) core_0_1 (
        .clk(clk),
        .rst_n(rst_n),

        .north_data_in(core_0_0_south_out),
        .north_data_out(core_0_1_north_out),

        .south_data_in(core_0_2_north_out),
        .south_data_out(core_0_1_south_out),

        .east_data_in(core_1_1_west_out),
        .east_data_out(core_0_1_east_out),

        .west_data_in({DATA_WIDTH{1'b0}}),
        .west_data_out(core_0_1_west_out),

        .router_in(router_0_1_to_core),
        .router_out(core_0_1_to_router)
    );

    core_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .CORE_X(1),
        .CORE_Y(1)
    ) core_1_1 (
        .clk(clk),
        .rst_n(rst_n),

        .north_data_in(core_1_0_south_out),
        .north_data_out(core_1_1_north_out),

        .south_data_in(core_1_2_north_out),
        .south_data_out(core_1_1_south_out),

        .east_data_in(core_2_1_west_out),
        .east_data_out(core_1_1_east_out),

        .west_data_in(core_0_1_east_out),
        .west_data_out(core_1_1_west_out),

        .router_in({DATA_WIDTH{1'b0}}),
        .router_out()
    );

    core_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .CORE_X(2),
        .CORE_Y(1)
    ) core_2_1 (
        .clk(clk),
        .rst_n(rst_n),

        .north_data_in(core_2_0_south_out),
        .north_data_out(core_2_1_north_out),

        .south_data_in(core_2_2_north_out),
        .south_data_out(core_2_1_south_out),

        .east_data_in({DATA_WIDTH{1'b0}}),
        .east_data_out(core_2_1_east_out),

        .west_data_in(core_1_1_east_out),
        .west_data_out(core_2_1_west_out),

        .router_in(router_2_1_to_core),
        .router_out(core_2_1_to_router)
    );

    core_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .CORE_X(0),
        .CORE_Y(2)
    ) core_0_2 (
        .clk(clk),
        .rst_n(rst_n),

        .north_data_in(core_0_1_south_out),
        .north_data_out(core_0_2_north_out),

        .south_data_in({DATA_WIDTH{1'b0}}),
        .south_data_out(core_0_2_south_out),

        .east_data_in(core_1_2_west_out),
        .east_data_out(core_0_2_east_out),

        .west_data_in({DATA_WIDTH{1'b0}}),
        .west_data_out(core_0_2_west_out),

        .router_in(router_0_2_to_core),
        .router_out(core_0_2_to_router)
    );

    core_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .CORE_X(1),
        .CORE_Y(2)
    ) core_1_2 (
        .clk(clk),
        .rst_n(rst_n),

        .north_data_in(core_1_1_south_out),
        .north_data_out(core_1_2_north_out),

        .south_data_in({DATA_WIDTH{1'b0}}),
        .south_data_out(core_1_2_south_out),

        .east_data_in(core_2_2_west_out),
        .east_data_out(core_1_2_east_out),

        .west_data_in(core_0_2_east_out),
        .west_data_out(core_1_2_west_out),

        .router_in(router_1_2_to_core),
        .router_out(core_1_2_to_router)
    );

    core_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .CORE_X(2),
        .CORE_Y(2)
    ) core_2_2 (
        .clk(clk),
        .rst_n(rst_n),

        .north_data_in(core_2_1_south_out),
        .north_data_out(core_2_2_north_out),

        .south_data_in({DATA_WIDTH{1'b0}}),
        .south_data_out(core_2_2_south_out),

        .east_data_in({DATA_WIDTH{1'b0}}),
        .east_data_out(core_2_2_east_out),

        .west_data_in(core_1_2_east_out),
        .west_data_out(core_2_2_west_out),

        .router_in(router_2_2_to_core),
        .router_out(core_2_2_to_router)
    );

    // ========================================
    // Router Instantiations
    // ========================================

    router_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .ROUTER_X(0),
        .ROUTER_Y(0)
    ) router_0_0 (
        .clk(clk),
        .rst_n(rst_n),

        .data_in
            (core_0_0_to_router),

        .data_out
            (router_0_0_to_core)
    );


    router_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .ROUTER_X(1),
        .ROUTER_Y(0)
    ) router_1_0 (
        .clk(clk),
        .rst_n(rst_n),

        .data_in
            (core_1_0_to_router),

        .data_out
            (router_1_0_to_core)
    );


    router_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .ROUTER_X(2),
        .ROUTER_Y(0)
    ) router_2_0 (
        .clk(clk),
        .rst_n(rst_n),

        .data_in
            (core_2_0_to_router),

        .data_out
            (router_2_0_to_core)
    );


    router_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .ROUTER_X(0),
        .ROUTER_Y(1)
    ) router_0_1 (
        .clk(clk),
        .rst_n(rst_n),

        .data_in
            (core_0_1_to_router),

        .data_out
            (router_0_1_to_core)
    );


    router_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .ROUTER_X(2),
        .ROUTER_Y(1)
    ) router_2_1 (
        .clk(clk),
        .rst_n(rst_n),

        .data_in
            (core_2_1_to_router),

        .data_out
            (router_2_1_to_core)
    );


    router_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .ROUTER_X(0),
        .ROUTER_Y(2)
    ) router_0_2 (
        .clk(clk),
        .rst_n(rst_n),

        .data_in
            (core_0_2_to_router),

        .data_out
            (router_0_2_to_core)
    );


    router_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .ROUTER_X(1),
        .ROUTER_Y(2)
    ) router_1_2 (
        .clk(clk),
        .rst_n(rst_n),

        .data_in
            (core_1_2_to_router),

        .data_out
            (router_1_2_to_core)
    );


    router_module #(
        .DATA_WIDTH(DATA_WIDTH),
        .ROUTER_X(2),
        .ROUTER_Y(2)
    ) router_2_2 (
        .clk(clk),
        .rst_n(rst_n),

        .data_in
            (core_2_2_to_router),

        .data_out
            (router_2_2_to_core)
    );


endmodule