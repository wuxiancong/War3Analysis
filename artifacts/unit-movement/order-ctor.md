# order ctor and lookup tail
## ctor
```
00286E80  lodsb    al, byte ptr [esi]
00286E81  mov      esi, 0x4c8b0023
00286E86  and      al, 0xc
00286E88  lea      edx, [esp + 0xc]
00286E8C  mov      dword ptr [esi + 0x20], ecx
00286E8F  push     edx
00286E90  mov      ecx, edi
00286E92  call     0x4c2d30
00286E97  mov      eax, dword ptr [esp + 0xc]
00286E9B  lea      ecx, [esp + 0xc]
00286E9F  push     ecx
00286EA0  mov      ecx, edi
00286EA2  mov      dword ptr [esi + 0x24], eax
00286EA5  call     0x4c2d30
00286EAA  mov      edx, dword ptr [esp + 0xc]
00286EAE  mov      dword ptr [esi + 0x28], edx
00286EB1  lea      edx, [esi + 0x2c]
00286EB4  mov      ecx, edi
00286EB6  call     0x2f110
00286EBB  pop      edi
00286EBC  pop      esi
00286EBD  ret      4
00286EC0  push     esi
00286EC1  mov      esi, ecx
00286EC3  mov      dword ptr [esi], 0x6f874ff4
00286EC9  call     0x17f0
00286ECE  test     byte ptr [esp + 8], 1
00286ED3  je       0x286ee4
00286ED5  push     0
00286ED7  push     -1
00286ED9  push     0x6f874f04
00286EDE  push     esi
00286EDF  call     0x6eb558
00286EE4  mov      eax, esi
00286EE6  pop      esi
00286EE7  ret      4
00286EEA  int3     
00286EEB  int3     
00286EEC  int3     
00286EED  int3     
00286EEE  int3     
00286EEF  int3     
00286EF0  push     esi
00286EF1  mov      esi, dword ptr [esp + 8]
00286EF5  push     edi
00286EF6  push     esi
00286EF7  mov      edi, ecx
00286EF9  call     0x1a30
00286EFE  add      edi, 0x38
00286F01  push     edi
```
## lookup_tail
```
0003FA80  setne    al
0003FA83  pop      esi
0003FA84  sub      eax, 1
0003FA87  and      eax, ecx
0003FA89  ret      
0003FA8A  mov      eax, dword ptr [esi + 0xc]
0003FA8D  mov      ecx, dword ptr [eax + ecx*8 + 4]
0003FA91  xor      eax, eax
0003FA93  cmp      dword ptr [ecx + 0x18], edx
0003FA96  pop      edi
0003FA97  setne    al
0003FA9A  pop      esi
0003FA9B  sub      eax, 1
0003FA9E  and      eax, ecx
0003FAA0  ret      
0003FAA1  int3     
0003FAA2  int3     
0003FAA3  int3     
0003FAA4  int3     
0003FAA5  int3     
0003FAA6  int3     
0003FAA7  int3     
0003FAA8  int3     
0003FAA9  int3     
0003FAAA  int3     
```
ucol idx 0x92AE84
66726f7374000000736c6565700000006c6f63757374737761726d00696d70616c65000066726f73746e6f766100000066726f737461726d6f726f6666000000
dwords 0x65656c73 0x70 0x75636f6c 0x77737473 0x6d7261 0x61706d69 0x656c 0x736f7266
