//@category War3Analysis
import ghidra.app.script.GhidraScript;
import ghidra.framework.model.DomainFile;
import ghidra.framework.model.DomainFolder;

public class ListProg extends GhidraScript {
    @Override
    public void run() throws Exception {
        println("project=" + state.getProject().getName());
        walk(getProjectRootFolder(), "");
    }

    private void walk(DomainFolder folder, String prefix) {
        println("folder " + prefix + folder.getName());
        for (DomainFile f : folder.getFiles()) {
            println("  file=" + f.getName() + " class=" + f.getContentType() + " path=" + f.getPathname());
        }
        for (DomainFolder sub : folder.getFolders()) {
            walk(sub, prefix + folder.getName() + "/");
        }
    }
}
