// Dump camera-distance related decompiles from War3_127.
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

public class DumpCamera extends GhidraScript {
    private static final String[] SEED_ADDRS = {
        "0x6f10d790", // CameraPropertyGetter (hook target)
        "0x6f03ae0a", // call site of CameraPropertyGetter
        "0x6f20e579", // imm float 1650.0 use
        "0x6f21a1b3", // imm float 1650.0 use
        "0x6f3434d5",
        "0x6f344bd9",
        "0x6f20b0ac", // 1200.0
        "0x6f34138b",
        "0x6f3429fd",
        "0x6f9714d0", // rdata 1650 default
        "0x6fa538b0", // rdata near 100/10000
        "0x6f0ef706", // 10000.0 use
    };

    @Override
    public void run() throws Exception {
        File out = new File("C:/War3Analysis/artifacts/camera-distance/ghidra-camera-dump.txt");
        out.getParentFile().mkdirs();
        PrintWriter pw = new PrintWriter(new FileWriter(out, false));
        try {
            pw.println("PROGRAM " + currentProgram.getName());
            pw.println("IMAGEBASE " + currentProgram.getImageBase());

            DecompInterface decomp = new DecompInterface();
            decomp.openProgram(currentProgram);
            try {
                Set<Function> seen = new LinkedHashSet<Function>();
                for (String a : SEED_ADDRS) {
                    Address addr = toAddr(a);
                    pw.println("\n### SEED " + a);
                    dumpXrefs(pw, addr, 40);
                    Function fn = getFunctionContaining(addr);
                    if (fn == null) {
                        pw.println("NO FUNCTION; insns:");
                        dumpInsns(pw, addr, 48);
                        continue;
                    }
                    if (seen.add(fn)) {
                        dumpFunction(pw, decomp, fn);
                    } else {
                        pw.println("already dumped " + fn.getName() + " @ " + fn.getEntryPoint());
                    }
                }

                // Follow xrefs from key constants
                dumpXrefFunctions(pw, decomp, seen, "0x6f9714d0", 20);
                dumpXrefFunctions(pw, decomp, seen, "0x6f951ea4", 20); // 1200 rdata
                dumpXrefFunctions(pw, decomp, seen, "0x6fa538b0", 20);
                dumpXrefFunctions(pw, decomp, seen, "0x6fa538b4", 20);
            } finally {
                decomp.dispose();
            }
        } finally {
            pw.close();
        }
        println("Wrote " + out.getAbsolutePath());
    }

    private void dumpXrefFunctions(PrintWriter pw, DecompInterface decomp, Set<Function> seen,
            String addrStr, int limit) throws Exception {
        Address addr = toAddr(addrStr);
        pw.println("\n### xref-funcs of " + addr);
        ReferenceManager rm = currentProgram.getReferenceManager();
        ReferenceIterator it = rm.getReferencesTo(addr);
        int n = 0;
        while (it.hasNext() && n < limit) {
            Reference r = it.next();
            Address from = r.getFromAddress();
            Function fn = getFunctionContaining(from);
            pw.println("  from " + from + " " + r.getReferenceType() +
                    (fn == null ? "" : (" in " + fn.getName() + "@" + fn.getEntryPoint())));
            if (fn != null && seen.add(fn)) {
                dumpFunction(pw, decomp, fn);
            }
            n++;
        }
    }

    private void dumpXrefs(PrintWriter pw, Address addr, int limit) {
        ReferenceManager rm = currentProgram.getReferenceManager();
        ReferenceIterator it = rm.getReferencesTo(addr);
        int n = 0;
        while (it.hasNext() && n < limit) {
            Reference r = it.next();
            Address from = r.getFromAddress();
            Function fn = getFunctionContaining(from);
            pw.println("  xref " + from + " " + r.getReferenceType() +
                    (fn == null ? "" : (" in " + fn.getName())));
            n++;
        }
        if (n == 0) {
            pw.println("  (no xrefs-to)");
        }
    }

    private void dumpFunction(PrintWriter pw, DecompInterface decomp, Function fn) throws Exception {
        pw.println("\n===== FUNCTION " + fn.getName() + " @ " + fn.getEntryPoint() +
                " size=" + fn.getBody().getNumAddresses() + " =====");
        dumpInsns(pw, fn.getEntryPoint(), 64);
        DecompileResults res = decomp.decompileFunction(fn, 120, monitor);
        if (res != null && res.decompileCompleted()) {
            pw.println("--- DECOMPILE ---");
            pw.println(res.getDecompiledFunction().getC());
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
