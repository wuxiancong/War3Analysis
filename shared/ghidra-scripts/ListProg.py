from ghidra.framework.model import ProjectData
print("PROJECT", currentProject.getName() if currentProject else None)
# Headless: currentProgram may be set after -process
print("PROGRAM", currentProgram)
if currentProgram:
    print(currentProgram.getName(), currentProgram.getExecutablePath(), currentProgram.getImageBase())
