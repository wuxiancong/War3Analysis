// 邮箱绑定页（EmailBindPanel）跳转逆向：定位相关字符串的引用函数，反编译其本身与调用者（2 层）。
// 用法（headless）：analyzeHeadless <projDir> <projName> -process game.dll -noanalysis -scriptPath <dir> -postScript DumpEmailBind.java
// 输出：D:/Qt/workspace/War3Analysis/artifacts/email-bind/<程序名>-<基址>.txt
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
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;

public class DumpEmailBind extends GhidraScript {
    private static final String[] STRINGS = {
        "EmailBindPanel", "NETMESSAGE_CONFIRMNOEMAILBIND", "NETMESSAGE_EMAILBIND",
        "NETERROR_NOEMAIL", "NETERROR_EMAILMISMATCH", "EBEmail", "ChangeEmailPanel"
    };

    @Override
    public void run() throws Exception {
        File dir = new File("D:/Qt/workspace/War3Analysis/artifacts/email-bind");
        dir.mkdirs();
        File out = new File(dir, currentProgram.getName() + "-" + currentProgram.getImageBase() + ".txt");
        PrintWriter pw = new PrintWriter(new FileWriter(out, false));
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        try {
            pw.println("PROGRAM " + currentProgram.getExecutablePath());
            pw.println("IMAGEBASE " + currentProgram.getImageBase());
            Set<Function> direct = new LinkedHashSet<>();
            for (String s : STRINGS) {
                Address strAddr = findStringAddress(s);
                pw.println("\n##### STRING " + s + " @ " + strAddr);
                if (strAddr == null) continue;
                for (Reference r : getReferencesTo(strAddr)) {
                    Function fn = getFunctionContaining(r.getFromAddress());
                    pw.println("  xref " + r.getFromAddress() + " in " + (fn == null ? "<none>" : fn.getName() + "@" + fn.getEntryPoint()));
                    if (fn != null) direct.add(fn);
                }
            }

            Set<Function> callers = new LinkedHashSet<>();
            for (Function fn : direct) {
                for (Function c : fn.getCallingFunctions(monitor)) {
                    if (!direct.contains(c)) callers.add(c);
                }
            }
            Set<Function> callers2 = new LinkedHashSet<>();
            for (Function fn : callers) {
                for (Function c : fn.getCallingFunctions(monitor)) {
                    if (!direct.contains(c) && !callers.contains(c)) callers2.add(c);
                }
            }

            pw.println("\n\n==================== DIRECT FUNCTIONS ====================");
            for (Function fn : direct) dumpFunction(pw, decomp, fn);
            pw.println("\n\n==================== CALLERS (level 1) ====================");
            for (Function fn : callers) dumpFunction(pw, decomp, fn);
            pw.println("\n\n==================== CALLERS (level 2) ====================");
            for (Function fn : callers2) dumpFunction(pw, decomp, fn);
        } finally {
            decomp.dispose();
            pw.close();
        }
        println("DumpEmailBind -> " + out.getAbsolutePath());
    }

    private Address findStringAddress(String s) {
        DataIterator it = currentProgram.getListing().getDefinedData(true);
        while (it.hasNext()) {
            Data d = it.next();
            Object v = d.getValue();
            if (v instanceof String && s.equals(v)) return d.getAddress();
        }
        // 未被识别为字符串时按字节搜索
        try {
            byte[] bytes = (s + "\0").getBytes("ISO-8859-1");
            return find(currentProgram.getMinAddress(), bytes);
        } catch (Exception e) {
            return null;
        }
    }

    private void dumpFunction(PrintWriter pw, DecompInterface decomp, Function fn) {
        pw.println("\n=== FUNCTION " + fn.getName() + " @ " + fn.getEntryPoint()
                   + " (RVA 0x" + Long.toHexString(fn.getEntryPoint().subtract(currentProgram.getImageBase())) + ") ===");
        StringBuilder callers = new StringBuilder();
        for (Function c : fn.getCallingFunctions(monitor)) callers.append(c.getEntryPoint()).append(' ');
        pw.println("callers: " + callers);
        DecompileResults res = decomp.decompileFunction(fn, 60, monitor);
        if (res != null && res.decompileCompleted()) {
            pw.println(res.getDecompiledFunction().getC());
        } else {
            pw.println("<decompile failed>");
        }
        pw.println("--- disasm ---");
        Instruction ins = getInstructionAt(fn.getEntryPoint());
        int n = 0;
        while (ins != null && fn.getBody().contains(ins.getAddress()) && n < 400) {
            pw.println(ins.getAddress() + "  " + bytesHex(ins) + "  " + ins);
            ins = ins.getNext();
            n++;
        }
    }

    private String bytesHex(Instruction ins) {
        StringBuilder sb = new StringBuilder();
        try {
            for (byte b : ins.getBytes()) sb.append(String.format("%02X ", b & 0xFF));
        } catch (Exception e) {
            return "??";
        }
        return String.format("%-24s", sb.toString().trim());
    }
}
