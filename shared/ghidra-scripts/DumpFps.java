// Decompile FPS-related functions from the existing War3_127 Ghidra project.
//@category War3Analysis
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.ReferenceManager;

public class DumpFps extends GhidraScript {
    private static final String[] ADDRS = {
        "0x6f35d2d0", "0x6f35c680", "0x6f179ce0", "0x6f179d50",
        "0x6f023e00", "0x6f025a70", "0x6f023240",
        "0x6f154c00", "0x6f154c70", "0x6f154d00", "0x6f154da0",
        "0x6f155000", "0x6f0ec500", "0x6f0f0c80", "0x6f0e8500"
    };

    @Override
    public void run() throws Exception {
        File out = new File("C:/War3Analysis/rea-out/ghidra-fps-dump.txt");
        out.getParentFile().mkdirs();
        PrintWriter pw = new PrintWriter(new FileWriter(out, false));
        try {
            pw.println("PROGRAM " + currentProgram.getName());
            pw.println("IMAGEBASE " + currentProgram.getImageBase());
            dumpString(pw, "maxfps", "0x6f951428");
            dumpString(pw, "lockfb", "0x6f95139c");
            dumpString(pw, "refreshrate", "0x6f951328");
            dumpString(pw, "FPS_fmt", "0x6f994009");
            dumpString(pw, "CGxDeviceD3d.cpp", "0x6f95d93c");

            DecompInterface decomp = new DecompInterface();
            decomp.openProgram(currentProgram);
            try {
                List<Function> seen = new ArrayList<Function>();
                for (String a : ADDRS) {
                    Address addr = toAddr(a);
                    Function fn = getFunctionContaining(addr);
                    if (fn == null) {
                        pw.println("\n=== NO FUNCTION AT " + a + " ===");
                        dumpInsns(pw, addr, 40);
                        continue;
                    }
                    if (seen.contains(fn)) {
                        continue;
                    }
                    seen.add(fn);
                    dumpFunction(pw, decomp, fn);
                }

                // Also decompile callers of Sleep IAT 0x6f94e188
                dumpXrefFunctions(pw, decomp, "0x6f94e188", 12);
                dumpXrefFunctions(pw, decomp, "0x6f94e1dc", 12); // QPC
                dumpXrefFunctions(pw, decomp, "0x6f94e4dc", 4); // wglSwapLayerBuffers
            } finally {
                decomp.dispose();
            }
        } finally {
            pw.close();
        }
        println("Wrote " + out.getAbsolutePath());
    }

    private void dumpString(PrintWriter pw, String name, String addrStr) {
        Address addr = toAddr(addrStr);
        pw.println("\n### xrefs to " + name + " " + addr);
        ReferenceManager rm = currentProgram.getReferenceManager();
        ReferenceIterator it = rm.getReferencesTo(addr);
        int n = 0;
        while (it.hasNext()) {
            Reference r = it.next();
            pw.println("  " + r.getFromAddress() + " " + r.getReferenceType() + " " + r.getSource());
            n++;
            if (n > 40) {
                pw.println("  ...");
                break;
            }
        }
        if (n == 0) {
            pw.println("  (none)");
        }
    }

    private void dumpXrefFunctions(PrintWriter pw, DecompInterface decomp, String addrStr, int limit) throws Exception {
        Address addr = toAddr(addrStr);
        pw.println("\n### functions referencing " + addr);
        ReferenceManager rm = currentProgram.getReferenceManager();
        ReferenceIterator it = rm.getReferencesTo(addr);
        int n = 0;
        List<Function> seen = new ArrayList<Function>();
        while (it.hasNext() && n < limit) {
            Reference r = it.next();
            Function fn = getFunctionContaining(r.getFromAddress());
            pw.println("  xref " + r.getFromAddress() + " -> fn " + (fn == null ? "null" : fn.getEntryPoint()));
            if (fn != null && !seen.contains(fn)) {
                seen.add(fn);
                dumpFunction(pw, decomp, fn);
            }
            n++;
        }
    }

    private void dumpFunction(PrintWriter pw, DecompInterface decomp, Function fn) throws Exception {
        pw.println("\n======== FUNCTION " + fn.getName() + " @ " + fn.getEntryPoint()
                + " - " + fn.getBody().getMaxAddress() + " ========");
        dumpInsns(pw, fn.getEntryPoint(), 80);
        DecompileResults res = decomp.decompileFunction(fn, 60, monitor);
        if (res != null && res.decompileCompleted()) {
            pw.println("--- decompile ---");
            pw.println(res.getDecompiledFunction().getC());
        } else {
            pw.println("--- decompile FAILED ---");
            if (res != null) {
                pw.println(res.getErrorMessage());
            }
        }
    }

    private void dumpInsns(PrintWriter pw, Address start, int count) {
        Instruction ins = currentProgram.getListing().getInstructionAt(start);
        if (ins == null) {
            ins = currentProgram.getListing().getInstructionAfter(start.subtract(1));
        }
        int n = 0;
        while (ins != null && n < count) {
            pw.println(String.format("  %s  %s", ins.getAddress(), ins.toString()));
            ins = ins.getNext();
            n++;
        }
    }
}
