// Dump CMinimap / click-event / SetCameraPosition related decompiles.
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

public class DumpMinimapViewport extends GhidraScript {
    private static final String[] SEED_ADDRS = {
        // CMinimapClickEvent / DragEvent / Event vftable methods
        "0x6f38ac50",
        "0x6f38ac80",
        "0x6f38acb0",
        "0x6f38ac20",
        // CMinimap vftable cluster (likely draw / input / camera-rect)
        "0x6f3a45a0",
        "0x6f3a3120",
        "0x6f3a2e10",
        "0x6f3a30d0",
        "0x6f3a2fa0",
        "0x6f09ba50",
        "0x6f0a22b0",
        "0x6f0a2270",
        // MapPing string use site
        "0x6f3934d8",
        // SetCameraPosition native name / impl candidates
        "0x6f1ee6c3",
        "0x6f6fa97b",
        "0x6f96e630",
        // vftables
        "0x6f99244c",
        "0x6f99256c",
        "0x6f992578",
    };

    private static final String[] XREF_SEEDS = {
        "0x6f99244c", // CMinimap vftable
        "0x6f99256c", // CMinimapClickEvent vftable
        "0x6f992578", // CMinimapDragEvent vftable
        "0x6f992c54", // "MapPing"
        "0x6f96e630", // "SetCameraPosition"
        "0x6f96e644", // "SetCameraQuickPosition"
        "0x6f96e67c", // "PanCameraTo"
    };

    @Override
    public void run() throws Exception {
        File out = new File("C:/War3Analysis/artifacts/minimap-viewport/ghidra-minimap-dump.txt");
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
                        dumpInsns(pw, addr, 64);
                        continue;
                    }
                    if (seen.add(fn)) {
                        dumpFunction(pw, decomp, fn);
                    } else {
                        pw.println("already dumped " + fn.getName() + " @ " + fn.getEntryPoint());
                    }
                }
                for (String a : XREF_SEEDS) {
                    dumpXrefFunctions(pw, decomp, seen, a, 30);
                }
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
        dumpInsns(pw, fn.getEntryPoint(), 80);
        DecompileResults res = decomp.decompileFunction(fn, 180, monitor);
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
