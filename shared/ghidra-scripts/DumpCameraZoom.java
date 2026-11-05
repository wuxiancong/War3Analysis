//@category War3Analysis
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.ReferenceManager;

public class DumpCameraZoom extends GhidraScript {
    private static final String[] ADDRS = {
        "0x6f20b093", "0x6f341375", "0x6f3429e5",
        "0x6f108e10", "0x6f0527e0", "0x6f0529d0",
        "0x6f037350", "0x6f03afb0", "0x6f20b0ac"
    };
    @Override
    public void run() throws Exception {
        File out = new File("C:/War3Analysis/artifacts/camera-distance/ghidra-camera-zoom.txt");
        out.getParentFile().mkdirs();
        PrintWriter pw = new PrintWriter(new FileWriter(out, false));
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        try {
            for (String a : ADDRS) {
                Address addr = toAddr(a);
                pw.println("\n### SEED " + a);
                ReferenceManager rm = currentProgram.getReferenceManager();
                ReferenceIterator it = rm.getReferencesTo(addr);
                int n=0;
                while (it.hasNext() && n++<30) {
                    Reference r = it.next();
                    Function f = getFunctionContaining(r.getFromAddress());
                    pw.println("  xref " + r.getFromAddress() + " " + r.getReferenceType() + (f==null?"":(" in "+f.getName())));
                }
                Function fn = getFunctionContaining(addr);
                if (fn == null) { dumpInsns(pw, addr, 80); continue; }
                pw.println("===== " + fn.getName() + " @ " + fn.getEntryPoint() + " =====");
                dumpInsns(pw, fn.getEntryPoint(), 100);
                DecompileResults res = decomp.decompileFunction(fn, 180, monitor);
                if (res != null && res.decompileCompleted()) {
                    pw.println("--- DECOMPILE ---");
                    pw.println(res.getDecompiledFunction().getC());
                }
            }
            // also dump callers of 20b0xx function
            Function zoom = getFunctionContaining(toAddr("0x6f20b093"));
            if (zoom != null) {
                pw.println("\n### callers of " + zoom.getName());
                for (Reference r : getReferencesTo(zoom.getEntryPoint())) {
                    Function f = getFunctionContaining(r.getFromAddress());
                    pw.println("  " + r.getFromAddress() + (f==null?"":(" in "+f.getName()+"@"+f.getEntryPoint())));
                    if (f != null && !f.equals(zoom)) {
                        DecompileResults res = decomp.decompileFunction(f, 180, monitor);
                        if (res != null && res.decompileCompleted()) {
                            pw.println("--- CALLER DECOMPILE " + f.getName() + " ---");
                            pw.println(res.getDecompiledFunction().getC());
                        }
                    }
                }
            }
        } finally {
            decomp.dispose();
            pw.close();
        }
        println("Wrote " + out.getAbsolutePath());
    }
    private void dumpInsns(PrintWriter pw, Address start, int count) {
        Address a = start;
        for (int i = 0; i < count; i++) {
            Instruction insn = getInstructionAt(a);
            if (insn == null) break;
            pw.println(String.format("  %s  %s", a, insn.toString()));
            a = a.add(insn.getLength());
        }
    }
}
