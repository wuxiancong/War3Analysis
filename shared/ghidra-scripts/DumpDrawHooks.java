// Decompile D3D Release / OpenGL ScenePresent / OpenGL display-reset from War3_127.
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

public class DumpDrawHooks extends GhidraScript {
    private static final String[] ADDRS = {
        "0x6f0ec510", // D3D device Release + null +0x584
        "0x6f0f0cc0", // GL ScenePresent
        "0x6f0e7670"  // GL display reset
    };

    @Override
    public void run() throws Exception {
        File out = new File("D:/Qt/workspace/War3Analysis/artifacts/draw-hooks/ghidra-127-draw-hooks.txt");
        out.getParentFile().mkdirs();
        PrintWriter pw = new PrintWriter(new FileWriter(out, false));
        try {
            pw.println("PROGRAM " + currentProgram.getName());
            pw.println("IMAGEBASE " + currentProgram.getImageBase());
            DecompInterface decomp = new DecompInterface();
            decomp.openProgram(currentProgram);
            try {
                for (String a : ADDRS) {
                    Address addr = toAddr(a);
                    Function fn = getFunctionContaining(addr);
                    pw.println("\n===== ADDR " + a + " =====");
                    if (fn == null) {
                        pw.println("NO FUNCTION");
                        dumpInsns(pw, addr, 25);
                        continue;
                    }
                    pw.println("FUNCTION " + fn.getName() + " entry " + fn.getEntryPoint()
                            + " max " + fn.getBody().getMaxAddress());
                    pw.println("HOOK_INSIDE " + (fn.getEntryPoint().equals(addr) ? "entry" : "interior"));
                    dumpInsns(pw, fn.getEntryPoint(), 60);
                    DecompileResults res = decomp.decompileFunction(fn, 90, monitor);
                    if (res != null && res.decompileCompleted()) {
                        pw.println("--- decompile ---");
                        pw.println(res.getDecompiledFunction().getC());
                    } else {
                        pw.println("--- decompile FAILED ---");
                        if (res != null) pw.println(res.getErrorMessage());
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

    private void dumpInsns(PrintWriter pw, Address start, int count) {
        Instruction ins = currentProgram.getListing().getInstructionAt(start);
        if (ins == null) {
            ins = currentProgram.getListing().getInstructionContaining(start);
        }
        int n = 0;
        while (ins != null && n < count) {
            pw.println(String.format("  %s  %s", ins.getAddress(), ins.toString()));
            ins = ins.getNext();
            n++;
        }
    }
}
