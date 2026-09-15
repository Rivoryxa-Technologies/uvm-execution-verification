# Executed open-source UVM ALU evidence

This repository answers a narrow feasibility question with executable evidence:
can the public Rivoryxa UVM ALU environment be elaborated and run, including
its classes and scoreboard, using an open-source simulator?

Yes. The runner fetches these immutable public inputs:

- [Rivoryxa UVM ALU testbench](https://github.com/Rivoryxa-Technologies/uvm-alu-testbench), commit `6f885404ba5cda6ed7699cdef54abf1c6949cdaf`
- [Accellera UVM 2020.3.1](https://github.com/accellera-official/uvm-core), commit `78c06547a2a0a29b3dc9dcafae62b75b2ff61544`

It uses Verilator `--binary --timing` to elaborate the complete UVM package,
sequence, sequencer, driver, monitor, analysis connections, scoreboard, and
test. A passing simulation must report exactly 200 scoreboard matches, zero
mismatches, zero UVM errors, and zero UVM fatals. The default matrix runs seeds
1, 17, and 2026.

The runner also applies a small, recorded test-only fault instrumentation patch
to the fetched DUT and compiles that instrumented source once. Correct runs use
the generated model with the fault disabled; the evidence retains both the
original upstream hash, instrumented hash, and exact patch.
With seed 17 and `+INJECT_MISMATCH`, the DUT returns an incorrect all-ones
result. That run passes the regression only when all 200 transactions reach the
scoreboard, at least one mismatch and UVM error are reported, the named
`SCB_MISMATCH_EXPECTED` marker appears, and simulation exits normally. A crash,
timeout, lint success, or arbitrary error cannot substitute for the expected
scoreboard evidence.

## Run from a fresh clone

Install Git, Python 3, a C++ compiler, make, and a recent Verilator 5 release.
The recorded local run used Verilator 5.050. Then run:

```sh
git clone https://github.com/Rivoryxa-Technologies/uvm-execution-verification
cd uvm-execution-verification
make test
```

No Python packages or commercial simulator licenses are required. Building the
UVM model is C++ compilation-intensive and may take several minutes. Each
fetch, build, and simulation has a bounded process-group timeout; override the
default 600 seconds when needed. Compilation is capped at two parallel jobs to
bound memory use on small runners:

```sh
python3 tools/run.py --timeout 600
```

Evidence is retained under `artifacts/<UTC run id>/`: combined logs for both
pinned fetches, the complete Verilator build, tool version, and every
simulation, plus `summary.json` with timings, revisions, seeds, classifications,
source hashes, and the runner hash.

## Portability and limits

The build defines Accellera's `UVM_NO_DPI` compatibility mode. This avoids a
platform-specific DPI C header dependency and disables DPI-backed component
name validation. It does not remove UVM class elaboration or the executed
sequence, driver, monitor, analysis ports, and scoreboard. Verilator 5.050 also
warns that the class-member opcode covergroup is ignored, so this evidence does
not claim functional coverage collection.

This is finite simulation evidence for three recorded passing seeds and one
recorded fault seed. It is not formal proof, exhaustive stimulus, or evidence
for every Verilator/UVM/platform combination. The fetched UVM and ALU sources
are removed after each run; their immutable revisions and hashes remain in the
evidence.

## License provenance

This orchestration code is MIT licensed. The runner fetches but does not
redistribute the ALU repository, which declares MIT, and Accellera UVM, which
declares Apache-2.0. Their own license and notice files govern those fetched
sources.
