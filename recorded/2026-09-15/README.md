# Independent UVM execution, 15 September 2026

A clean local clone at `44b61d4` ran `make test`, freshly fetching both pinned public source repositories. Verilator 5.050 elaborated and ran the UVM classes on macOS ARM64. Correct seeds 1, 17, and 2026 each reported 200 matches, zero mismatches, zero UVM errors, and zero fatals. The fault-enabled seed 17 reported scoreboard mismatches and the required marker. All eight then-current runner tests passed.

The stricter classifier in `2096995` was independently applied to all four retained logs and accepted the same outcomes. Its nine unit tests pass, including a regression rejecting duplicate severity summaries that could hide an error. CI runs the complete final pipeline.

The original and instrumented DUT hashes, exact patch, source revisions, seeds, tools, commands, and durations are retained. Normal cases run with fault injection disabled in the instrumented DUT. UVM class-member covergroups are ignored by this Verilator run; no collected functional coverage is claimed. UVM_NO_DPI disables DPI-backed name checking. See the root README for scope and licensing.
