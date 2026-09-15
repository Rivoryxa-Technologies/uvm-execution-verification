#!/usr/bin/env python3
"""Run a pinned public UVM ALU testbench with pinned Accellera UVM."""
import argparse, datetime as dt, difflib, hashlib, json, math, os, platform, re, shutil, signal, subprocess, sys, time, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALU_URL = "https://github.com/Rivoryxa-Technologies/uvm-alu-testbench.git"
ALU_REV = "6f885404ba5cda6ed7699cdef54abf1c6949cdaf"
UVM_URL = "https://github.com/accellera-official/uvm-core.git"
UVM_REV = "78c06547a2a0a29b3dc9dcafae62b75b2ff61544"  # tag 2020.3.1

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def execute(cmd, cwd, timeout, log):
    start=time.monotonic(); timed=False
    try:
        p=subprocess.Popen(cmd,cwd=str(cwd),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=(os.name=="posix"))
        try: output,_=p.communicate(timeout=timeout); rc=p.returncode
        except subprocess.TimeoutExpired:
            timed=True
            os.killpg(p.pid,signal.SIGKILL) if os.name=="posix" else p.kill()
            output,_=p.communicate(); output=(output or "")+"\nRUNNER_TIMEOUT\n"; rc=124
    except OSError as e: output="RUNNER_EXEC_ERROR: %s\n"%e; rc=127
    log.parent.mkdir(parents=True,exist_ok=True); log.write_text(output or "")
    return {"command":cmd,"returncode":rc,"timed_out":timed,"seconds":round(time.monotonic()-start,6),"log":log.name},output or ""

def classify(output, rc, timed, mutant):
    counts=re.findall(r"UVM_(INFO|WARNING|ERROR|FATAL)\s*:\s*(\d+)",output)
    severity={k:int(v) for k,v in counts} if len(counts)==4 else {}
    scoreboard=re.findall(r"\[SCB\] matched=(\d+) mismatched=(\d+)",output)
    if len(scoreboard)!=1 or len(counts)!=4 or timed: return False
    matched,mismatched=map(int,scoreboard[0])
    if mutant:
        return (rc==0 and matched+mismatched==200 and mismatched>0 and
                severity.get("ERROR",0)>0 and severity.get("FATAL")==0 and
                "SCB_MISMATCH_EXPECTED" in output)
    return rc==0 and matched==200 and mismatched==0 and severity.get("ERROR")==0 and severity.get("FATAL")==0

def fetch(git,url,rev,dest,timeout,logs):
    dest.mkdir(); steps=[]
    for name,cmd in [("init",[git,"init","-q"]),("fetch",[git,"fetch","--depth","1",url,rev]),("checkout",[git,"checkout","-q","--detach","FETCH_HEAD"])]:
        rec,_=execute(cmd,dest,timeout,logs/(name+".log")); steps.append(rec)
        if rec["returncode"]: return steps, ""
    rec,out=execute([git,"rev-parse","HEAD"],dest,timeout,logs/"revision.log"); steps.append(rec)
    return steps,out.strip()

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--timeout",type=float,default=600); ap.add_argument("--artifacts",type=Path,default=ROOT/"artifacts"); args=ap.parse_args(argv)
    if not math.isfinite(args.timeout) or args.timeout<=0: ap.error("timeout must be positive and finite")
    git,verilator=shutil.which("git"),shutil.which("verilator")
    if not git or not verilator: print("ERROR missing: "+", ".join(n for n,v in (("git",git),("verilator",verilator)) if not v),file=sys.stderr); return 2
    rid=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")+"-"+uuid.uuid4().hex[:8]; out=args.artifacts.resolve()/rid; work=out/"work"; logs=out/"logs"; work.mkdir(parents=True)
    allsteps=[]; astep,arev=fetch(git,ALU_URL,ALU_REV,work/"alu",args.timeout,logs/"alu-fetch"); allsteps+=astep
    ustep,urev=fetch(git,UVM_URL,UVM_REV,work/"uvm",args.timeout,logs/"uvm-fetch"); allsteps+=ustep
    cases=[]; original_sources={}; patched_dut_hash=None
    overall=arev==ALU_REV and urev==UVM_REV and all(s["returncode"]==0 for s in allsteps)
    if overall:
        alu=work/"alu"; dut=alu/"rtl/alu.sv"; original=dut.read_text()
        for rel in ("rtl/alu.sv","tb/alu_if.sv","tb/alu_pkg.sv","tb/tb_top.sv"):
            original_sources[rel]=sha(alu/rel)
        needle="      unique case (op)"
        patched=original.replace(needle,"      if ($test$plusargs(\"INJECT_MISMATCH\") && in_valid) begin\n        $display(\"SCB_MISMATCH_EXPECTED\");\n        result <= '1;\n      end else\n"+needle,1)
        if patched==original: overall=False
        else:
            dut.write_text(patched); patched_dut_hash=sha(dut)
            (out/"instrumentation.patch").write_text("".join(difflib.unified_diff(
                original.splitlines(True),patched.splitlines(True),fromfile="upstream/rtl/alu.sv",tofile="instrumented/rtl/alu.sv")))
    binary=work/"obj_dir/uvm_alu_sim"
    if overall:
        cmd=[verilator,"--binary","--timing","-j","2","-Wno-fatal","--top-module","tb_top","-DUVM_NO_DPI","-I"+str(work/"uvm/src"),str(work/"uvm/src/uvm_pkg.sv"),str(work/"alu/rtl/alu.sv"),str(work/"alu/tb/alu_if.sv"),str(work/"alu/tb/alu_pkg.sv"),str(work/"alu/tb/tb_top.sv"),"--Mdir",str(work/"obj_dir"),"-o","uvm_alu_sim"]
        build,_=execute(cmd,ROOT,args.timeout,logs/"build.log"); allsteps.append(build); overall &= build["returncode"]==0 and not build["timed_out"]
    if overall:
        for seed,mutant in ((1,False),(17,False),(2026,False),(17,True)):
            cmd=[str(binary),"+UVM_TESTNAME=alu_base_test","+UVM_NO_RELNOTES","+verilator+seed+"+str(seed)]
            if mutant: cmd += ["+INJECT_MISMATCH","+SCB_MISMATCH_EXPECTED"]
            rec,text=execute(cmd,ROOT,args.timeout,logs/("mutant-s17.log" if mutant else "correct-s%d.log"%seed))
            ok=classify(text,rec["returncode"],rec["timed_out"],mutant); cases.append({"seed":seed,"variant":"mismatch" if mutant else "correct","expected":"scoreboard mismatch" if mutant else "200 matches, zero errors","passed":ok,**rec}); overall &= ok
    verrec,version=execute([verilator,"--version"],ROOT,10,logs/"verilator-version.log")
    sources={}
    if (work/"alu").exists():
        for rel in ("tb/alu_if.sv","tb/alu_pkg.sv","tb/tb_top.sv"):
            path=work/"alu"/rel
            if path.is_file(): sources[rel]=sha(path)
    expected_cases=[(1,"correct"),(17,"correct"),(2026,"correct"),(17,"mismatch")]
    observed_cases=[(case["seed"],case["variant"]) for case in cases]
    overall &= observed_cases==expected_cases and all(case["passed"] for case in cases)
    summary={"schema_version":1,"passed":bool(overall),"alu":{"url":ALU_URL,"revision":arev,"expected_revision":ALU_REV},"uvm":{"url":UVM_URL,"revision":urev,"expected_revision":UVM_REV,"release":"2020.3.1","license":"Apache-2.0"},"verilator_version":version.strip(),"platform":platform.platform(),"python":platform.python_version(),"timeout_seconds":args.timeout,"original_source_sha256":original_sources,"instrumented_dut_sha256":patched_dut_hash,"unchanged_instrumented_source_sha256":sources,"instrumentation_patch":"instrumentation.patch" if patched_dut_hash else None,"steps":allsteps,"expected_cases":expected_cases,"cases":cases,"runner_sha256":sha(Path(__file__))}
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n"); shutil.rmtree(work,ignore_errors=True); print(("PASS" if overall else "FAIL")+" evidence: "+str(out/"summary.json")); return 0 if overall else 1

if __name__=="__main__": raise SystemExit(main())
