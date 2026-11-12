// Follow CMinimapClickEvent consumers and SetCameraPosition path.
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
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.ReferenceManager;

public class DumpMinimapViewport2 extends GhidraScript {
    private static final String[] SEED_ADDRS = {
        // 0x10064 immediate sites (CMinimapClickEvent type id)
        "0x6f219985",
        "0x6f34aaad",
        "0x6f34aab2",
        "0x6f3519d5",
        "0x6f3756dc",
        "0x6f3a0933",
        "0x6f3a09cc",
        "0x6f3a2e7d",
        "0x6f3c2c73",
        "0x6f67b751",
        // 0x10065 drag
        "0x6f34aae3",
        "0x6f3519ca",
        "0x6f3a025b",
        "0x6f3a303b",
        // helpers seen from click path
        "0x6f343250",
        "0x6f34f3a0",
        "0x6f34da20",
        "0x6f0991f0",
        "0x6f3b89f0",
        "0x6f3a3120",
        "0x6f0566d0",
        "0x6f0bc8d0",
        // SetCameraPosition registration / candidates
        "0x6f70a0c0",
        "0x6f6fa974",
        "0x6f1ee6c0",
        // camera field writer from prior analysis
        "0x6f345760",
        "0x6f341350",
    };

    @Override
    public void run() throws Exception {
        File out = new File("C:/War3Analysis/artifacts/minimap-viewport/ghidra-minimap-dump2.txt");
        out.getParentFile().mkdirs();
        PrintWriter pw = new PrintWriter(new FileWriter(out, false));
        try {
            pw.println("PROGRAM " + currentProgram.getName());
            DecompInterface decomp = new DecompInterface();
            decomp.openProgram(currentProgram);
            try {
                Set<Function> seen = new LinkedHashSet<Function>();
                for (String a : SEED_ADDRS) {
                    Address addr = toAddr(a);
                    pw.println("\n### SEED " + a);
                    Function fn = getFunctionContaining(addr);
                    if (fn == null) {
                        // try create
                        fn = createFunction(addr, null);
                    }
                    if (fn == null) {
                        pw.println("NO FUNCTION; insns:");
                        dumpInsns(pw, addr, 96);
                        continue;
                    }
                    pw.println("in " + fn.getName() + " @ " + fn.getEntryPoint() +
                            " size=" + fn.getBody().getNumAddresses());
                    if (seen.add(fn)) {
                        dumpFunction(pw, decomp, fn);
                    } else {
                        pw.println("already dumped");
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
        pw.println("\n===== FUNCTION " + fn.getName() + " @ " + fn.getEntryPoint() +
                " size=" + fn.getBody().getNumAddresses() + " =====");
        dumpInsns(pw, fn.getEntryPoint(), 48);
        long size = fn.getBody().getNumAddresses();
        if (size > 8000) {
            pw.println("SKIP FULL DECOMPILE (too large); dumping call sites mentioning nearby only");
            return;
        }
        DecompileResults res = decomp.decompileFunction(fn, 180, monitor);
        if (res != null && res.decompileCompleted()) {
            pw.println("--- DECOMPILE ---");
            String c = res.getDecompiledFunction().getC();
            if (c.length() > 25000) {
                c = c.substring(0, 25000) + "\n...TRUNC...\n";
            }
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
