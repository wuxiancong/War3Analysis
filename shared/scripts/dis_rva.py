import sys, pefile, capstone
path, rva, n = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3])
pe = pefile.PE(path)
base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_data(rva, n)
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for i in md.disasm(data, rva):
    print("%08X  %-10s %s" % (i.address, i.mnemonic, i.op_str))
