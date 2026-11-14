// 通用：反编译包含指定地址的函数（含调用者列表与反汇编）。
// 用法：analyzeHeadless <projDir> <proj> -process game.dll -noanalysis -scriptPath <dir> -postScript DumpAt.java <输出名> <addr1> [addr2 ...]
// 输出：D:/Qt/workspace/War3Analysis/artifacts/email-bind/<输出名>.txt
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

public class DumpAt extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            println("usage: DumpAt.java <outName> <addr>...");
            return;
        }
        File dir = new File("D:/Qt/workspace/War3Analysis/artifacts/email-bind");
        dir.mkdirs();
        File out = new File(dir, args[0] + ".txt");
        PrintWriter pw = new PrintWriter(new FileWriter(out, false));
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        try {
            pw.println("PROGRAM " + currentProgram.getExecutablePath() + " IMAGEBASE " + currentProgram.getImageBase());
            Set<Function> seen = new LinkedHashSet<>();
            for (int i = 1; i < args.length; i++) {
                Address a = toAddr(args[i]);
                Function fn = getFunctionContaining(a);
                pw.println("\n##### ADDR " + args[i] + " -> " + (fn == null ? "<no function>" : fn.getName() + "@" + fn.getEntryPoint()));
                if (fn == null || !seen.add(fn)) continue;
                pw.println("\n=== FUNCTION " + fn.getName() + " @ " + fn.getEntryPoint()
                           + " (RVA 0x" + Long.toHexString(fn.getEntryPoint().subtract(currentProgram.getImageBase())) + ") ===");
                StringBuilder callers = new StringBuilder();
                for (Function c : fn.getCallingFunctions(monitor)) callers.append(c.getEntryPoint()).append(' ');
                pw.println("callers: " + callers);
                DecompileResults res = decomp.decompileFunction(fn, 90, monitor);
                pw.println(res != null && res.decompileCompleted() ? res.getDecompiledFunction().getC() : "<decompile failed>");
                pw.println("--- disasm ---");
                Instruction ins = getInstructionAt(fn.getEntryPoint());
                int n = 0;
                while (ins != null && fn.getBody().contains(ins.getAddress()) && n < 600) {
                    StringBuilder hb = new StringBuilder();
                    for (byte b : ins.getBytes()) hb.append(String.format("%02X ", b & 0xFF));
                    pw.println(ins.getAddress() + "  " + String.format("%-24s", hb.toString().trim()) + "  " + ins);
                    ins = ins.getNext();
                    n++;
                }
            }
        } finally {
            decomp.dispose();
            pw.close();
        }
        println("DumpAt -> " + out.getAbsolutePath());
    }
}
