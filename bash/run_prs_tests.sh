#!/bin/bash
# Run all 2-phase PRS simulations.
#
# Run from the project root:
#   cd ACT_files/02211-final_project && bash bash/run_prs_tests.sh

echo "============================================"
echo "Input Block PRS"
echo "============================================"
actsim -Wlang_subst:off test/prs/test_input_block.act test_input_block < scripts/prs/input_block_test.script

echo "============================================"
echo "Arbiter 4 PRS"
echo "============================================"
actsim -Wlang_subst:off test/prs/test_arbiter_4_prs.act test_arbiter_4_prs < scripts/prs/arbiter_4_prs_test.script

echo "============================================"
echo "Router PRS"
echo "============================================"
actsim -Wlang_subst:off test/prs/test_router_prs.act test_router_prs < scripts/prs/router_prs_test.script

echo "============================================"
echo "All PRS simulations complete."
echo "============================================"
