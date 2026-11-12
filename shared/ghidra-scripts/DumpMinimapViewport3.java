// Decompile the actual CMinimapClickEvent handler and camera-move callee.
//@category War3Analysis
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.LinkedHashSet;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.SourceType;

public class DumpMinimapViewport3 extends GhidraScript {
    private static final String[] SEED_ADDRS = {
        "0x6f3a4aa0", // CMinimapClickEvent handler
        "0x6f3a76d0", // camera move from click (computed)
        "0x6f3a5df0",
        "0x6f3a0fa0",
        "0x6f3a1f00",
        "0x6f3a6ac0",
        "0x6f3b89f0", // draw/update candidate
        "0x6f3a3120", // CMinimap draw vfunc candidate
        "0x6f0e44a0",
        "0x6f0d0af0",
        "0x6f345760",
    };

    @Override
    public void run() throws Exception {
        File out = new File("C:/War3Analysis/artifacts/minimap-viewport/ghidra-minimap-dump3.txt");
        out.getParentFile().mkdirs();
        PrintWriter pw = new PrintWriter(new FileWriter(out, false));
        try {
            DecompInterface decomp = new DecompInterface();
            decomp.openProgram(currentProgram);
            try {
                Set<Function> seen = new LinkedHashSet<Function>();
                for (String a : SEED_ADDRS) {
                    Address addr = toAddr(a);
                    pw.println("\n### SEED " + a);
                    Function fn = getFunctionContaining(addr);
                    if (fn == null || fn.getEntryPoint().getOffset() != addr.getOffset()) {
                        // clear bogus size-1 and recreate
                        if (fn != null && fn.getBody().getNumAddresses() <= 1) {
                            removeFunction(fn);
                        }
                        disassemble(addr);
                        fn = createFunction(addr, null);
                    }
                    if (fn == null) {
                        pw.println("NO FUNCTION");
                        dumpInsns(pw, addr, 80);
                        continue;
                    }
                    if (seen.add(fn)) {
                        dumpFunction(pw, decomp, fn);
                    } else {
                        pw.println("already " + fn.getName());
                    }
                }
            } finally {
                decomp.dispose();
            }
        } finally {
            pw.close();
        }
        println("Wrote " + out.getAbsolutePath());
    }

    private void dumpFunction(PrintWriter pw, DecompInterface decomp, Function fn) throws Exception {
        pw.println("===== FUNCTION " + fn.getName() + " @ " + fn.getEntryPoint() +
                " size=" + fn.getBody().getNumAddresses() + " =====");
        dumpInsns(pw, fn.getEntryPoint(), 64);
        DecompileResults res = decomp.decompileFunction(fn, 200, monitor);
        if (res != null && res.decompileCompleted()) {
            pw.println("--- DECOMPILE ---");
            String c = res.getDecompiledFunction().getC();
            if (c.length() > 30000) c = c.substring(0, 30000) + "\n...TRUNC...\n";
            pw.println(c);
        } else {
            pw.println("DECOMPILE FAILED");
        }
    }

    private void dumpInsns(PrintWriter pw, Address start, int count) {
        Address a = start;
        for (int i = 0; i < count; i++) {
            Instruction insn = getInstructionAt(a);
            if (insn == null) {
                pw.println(String.format("  %s  ??", a));
                break;
            }
            pw.println(String.format("  %s  %s", a, insn.toString()));
            a = a.add(insn.getLength());
        }
    }
}
