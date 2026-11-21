# older offset spot check
## 1.0.17
### fly
```
002C0FB0  push     ebp
002C0FB1  mov      ebp, esp
002C0FB3  sub      esp, 8
002C0FB6  mov      ecx, dword ptr [0x6f87125c]
002C0FBC  push     ebx
002C0FBD  xor      ebx, ebx
002C0FBF  push     edi
002C0FC0  mov      dword ptr [ebp - 4], ebx
002C0FC3  call     0x29b1c0
002C0FC8  mov      ecx, dword ptr [ebp + 8]
002C0FCB  test     ecx, ecx
002C0FCD  je       0x2c104b
002C0FCF  push     esi
002C0FD0  push     ecx
002C0FD1  mov      ecx, eax
002C0FD3  call     0x326f00
002C0FD8  push     ebx
002C0FD9  lea      ecx, [ebp - 8]
```
### order
```
002C53F0  push     ebp
002C53F1  mov      ebp, esp
002C53F3  sub      esp, 8
002C53F6  mov      ecx, dword ptr [0x6f87125c]
002C53FC  push     ebx
002C53FD  push     esi
002C53FE  xor      ebx, ebx
002C5400  push     edi
002C5401  mov      dword ptr [ebp - 4], ebx
002C5404  call     0x29b1c0
002C5409  mov      ecx, dword ptr [ebp + 8]
002C540C  test     ecx, ecx
002C540E  je       0x2c54e5
002C5414  push     ecx
002C5415  mov      ecx, eax
002C5417  call     0x326f00
002C541C  push     ebx
002C541D  lea      ecx, [ebp - 8]
002C5420  mov      esi, eax
002C5422  call     0xff620
002C5427  push     esi
002C5428  lea      ecx, [ebp - 8]
002C542B  call     0xf60b0
002C5430  mov      esi, dword ptr [ebp - 8]
002C5433  test     esi, esi
002C5435  je       0x2c544e
002C5437  mov      ecx, esi
002C5439  call     0xed8a0
002C543E  test     eax, eax
002C5440  je       0x2c544e
002C5442  mov      ecx, dword ptr [eax + 0x20]
002C5445  test     ecx, ecx
002C5447  jne      0x2c544e
002C5449  lea      eax, [ebp - 8]
002C544C  jmp      0x2c5460
002C544E  push     0
002C5450  lea      ecx, [ebp + 8]
002C5453  mov      ebx, 1
002C5458  call     0xf6050
002C545D  mov      esi, dword ptr [ebp - 8]
```
### x
```
002BF640  push     ebp
002BF641  mov      ebp, esp
002BF643  sub      esp, 0x14
002BF646  mov      ecx, dword ptr [0x6f87125c]
002BF64C  push     ebx
002BF64D  xor      ebx, ebx
002BF64F  push     edi
002BF650  mov      dword ptr [ebp - 4], ebx
002BF653  call     0x29b1c0
002BF658  mov      ecx, dword ptr [ebp + 8]
002BF65B  test     ecx, ecx
002BF65D  je       0x2bf6db
002BF65F  push     esi
002BF660  push     ecx
002BF661  mov      ecx, eax
002BF663  call     0x326f00
002BF668  push     ebx
002BF669  lea      ecx, [ebp - 8]
002BF66C  mov      esi, eax
002BF66E  call     0xff620
002BF673  push     esi
002BF674  lea      ecx, [ebp - 8]
```
### speed
```
002BFD90  push     ebp
002BFD91  mov      ebp, esp
002BFD93  sub      esp, 8
002BFD96  mov      ecx, dword ptr [0x6f87125c]
002BFD9C  push     ebx
002BFD9D  xor      ebx, ebx
002BFD9F  push     edi
002BFDA0  mov      dword ptr [ebp - 4], ebx
002BFDA3  call     0x29b1c0
002BFDA8  mov      ecx, dword ptr [ebp + 8]
002BFDAB  test     ecx, ecx
002BFDAD  je       0x2bfe6d
002BFDB3  push     esi
002BFDB4  push     ecx
002BFDB5  mov      ecx, eax
002BFDB7  call     0x326f00
002BFDBC  push     ebx
002BFDBD  lea      ecx, [ebp - 8]
002BFDC0  mov      esi, eax
002BFDC2  call     0xff620
002BFDC7  push     esi
002BFDC8  lea      ecx, [ebp - 8]
002BFDCB  call     0xf60b0
002BFDD0  mov      esi, dword ptr [ebp - 8]
002BFDD3  test     esi, esi
002BFDD5  je       0x2bfdee
002BFDD7  mov      ecx, esi
002BFDD9  call     0xed8a0
```
## 1.21
### fly
```
002C46A0  push     ebp
002C46A1  mov      ebp, esp
002C46A3  sub      esp, 8
002C46A6  mov      ecx, dword ptr [0x6f873334]
002C46AC  push     ebx
002C46AD  xor      ebx, ebx
002C46AF  push     edi
002C46B0  mov      dword ptr [ebp - 4], ebx
002C46B3  call     0x29e5c0
002C46B8  mov      ecx, dword ptr [ebp + 8]
002C46BB  test     ecx, ecx
002C46BD  je       0x2c473b
002C46BF  push     esi
002C46C0  push     ecx
002C46C1  mov      ecx, eax
002C46C3  call     0x32b6d0
002C46C8  push     ebx
002C46C9  lea      ecx, [ebp - 8]
```
### order
```
002C8AE0  push     ebp
002C8AE1  mov      ebp, esp
002C8AE3  sub      esp, 8
002C8AE6  mov      ecx, dword ptr [0x6f873334]
002C8AEC  push     ebx
002C8AED  push     esi
002C8AEE  xor      ebx, ebx
002C8AF0  push     edi
002C8AF1  mov      dword ptr [ebp - 4], ebx
002C8AF4  call     0x29e5c0
002C8AF9  mov      ecx, dword ptr [ebp + 8]
002C8AFC  test     ecx, ecx
002C8AFE  je       0x2c8bd5
002C8B04  push     ecx
002C8B05  mov      ecx, eax
002C8B07  call     0x32b6d0
002C8B0C  push     ebx
002C8B0D  lea      ecx, [ebp - 8]
002C8B10  mov      esi, eax
002C8B12  call     0xff650
002C8B17  push     esi
002C8B18  lea      ecx, [ebp - 8]
002C8B1B  call     0xf60e0
002C8B20  mov      esi, dword ptr [ebp - 8]
002C8B23  test     esi, esi
002C8B25  je       0x2c8b3e
002C8B27  mov      ecx, esi
002C8B29  call     0xed8a0
002C8B2E  test     eax, eax
002C8B30  je       0x2c8b3e
002C8B32  mov      ecx, dword ptr [eax + 0x20]
002C8B35  test     ecx, ecx
002C8B37  jne      0x2c8b3e
002C8B39  lea      eax, [ebp - 8]
002C8B3C  jmp      0x2c8b50
002C8B3E  push     0
002C8B40  lea      ecx, [ebp + 8]
002C8B43  mov      ebx, 1
002C8B48  call     0xf6080
002C8B4D  mov      esi, dword ptr [ebp - 8]
```
### x
```
002C2D30  push     ebp
002C2D31  mov      ebp, esp
002C2D33  sub      esp, 0x14
002C2D36  mov      ecx, dword ptr [0x6f873334]
002C2D3C  push     ebx
002C2D3D  xor      ebx, ebx
002C2D3F  push     edi
002C2D40  mov      dword ptr [ebp - 4], ebx
002C2D43  call     0x29e5c0
002C2D48  mov      ecx, dword ptr [ebp + 8]
002C2D4B  test     ecx, ecx
002C2D4D  je       0x2c2dcb
002C2D4F  push     esi
002C2D50  push     ecx
002C2D51  mov      ecx, eax
002C2D53  call     0x32b6d0
002C2D58  push     ebx
002C2D59  lea      ecx, [ebp - 8]
002C2D5C  mov      esi, eax
002C2D5E  call     0xff650
002C2D63  push     esi
002C2D64  lea      ecx, [ebp - 8]
```
### speed
```
002C3480  push     ebp
002C3481  mov      ebp, esp
002C3483  sub      esp, 8
002C3486  mov      ecx, dword ptr [0x6f873334]
002C348C  push     ebx
002C348D  xor      ebx, ebx
002C348F  push     edi
002C3490  mov      dword ptr [ebp - 4], ebx
002C3493  call     0x29e5c0
002C3498  mov      ecx, dword ptr [ebp + 8]
002C349B  test     ecx, ecx
002C349D  je       0x2c355d
002C34A3  push     esi
002C34A4  push     ecx
002C34A5  mov      ecx, eax
002C34A7  call     0x32b6d0
002C34AC  push     ebx
002C34AD  lea      ecx, [ebp - 8]
002C34B0  mov      esi, eax
002C34B2  call     0xff650
002C34B7  push     esi
002C34B8  lea      ecx, [ebp - 8]
002C34BB  call     0xf60e0
002C34C0  mov      esi, dword ptr [ebp - 8]
002C34C3  test     esi, esi
002C34C5  je       0x2c34de
002C34C7  mov      ecx, esi
002C34C9  call     0xed8a0
```
## 1.24.4
### fly
```
003C68E0  mov      ecx, dword ptr [esp + 4]
003C68E4  call     0x3be7f0
003C68E9  test     eax, eax
003C68EB  jne      0x3c68f3
003C68ED  mov      eax, dword ptr [0x6fac52cc]
003C68F2  ret      
```
### order
```
003C82C0  mov      ecx, dword ptr [esp + 4]
003C82C4  push     esi
003C82C5  call     0x3be7f0
003C82CA  mov      esi, eax
003C82CC  test     esi, esi
003C82CE  je       0x3c831f
003C82D0  mov      edx, dword ptr [esi + 0x10]
003C82D3  mov      ecx, dword ptr [esi + 0xc]
003C82D6  call     0x40770
003C82DB  test     eax, eax
003C82DD  je       0x3c831f
003C82DF  xor      ecx, ecx
003C82E1  cmp      dword ptr [eax + 0xc], 0x2b61676c
003C82E8  setne    cl
003C82EB  sub      ecx, 1
003C82EE  and      ecx, eax
003C82F0  mov      eax, ecx
003C82F2  je       0x3c831f
003C82F4  cmp      dword ptr [eax + 0x20], 0
003C82F8  jne      0x3c831f
003C82FA  mov      edx, dword ptr [esi + 0x1a0]
003C8300  and      edx, dword ptr [esi + 0x19c]
003C8306  lea      ecx, [esi + 0x19c]
003C830C  cmp      edx, -1
003C830F  je       0x3c831f
003C8311  call     0x4791c0
003C8316  test     eax, eax
003C8318  je       0x3c831f
003C831A  mov      eax, dword ptr [eax + 0x24]
003C831D  pop      esi
003C831E  ret      
```
### x
```
003C6050  mov      ecx, dword ptr [esp + 4]
003C6054  sub      esp, 0xc
003C6057  call     0x3be7f0
003C605C  test     eax, eax
003C605E  jne      0x3c6069
003C6060  mov      eax, dword ptr [0x6fac52cc]
003C6065  add      esp, 0xc
003C6068  ret      
```
### speed
```
003C6350  push     ecx
003C6351  mov      ecx, dword ptr [esp + 8]
003C6355  push     esi
003C6356  call     0x3be7f0
003C635B  mov      esi, eax
003C635D  test     esi, esi
003C635F  je       0x3c639c
003C6361  mov      edx, dword ptr [esi + 0x10]
003C6364  mov      ecx, dword ptr [esi + 0xc]
003C6367  call     0x40770
003C636C  test     eax, eax
003C636E  je       0x3c639c
003C6370  xor      ecx, ecx
003C6372  cmp      dword ptr [eax + 0xc], 0x2b61676c
003C6379  setne    cl
003C637C  sub      ecx, 1
003C637F  and      ecx, eax
003C6381  mov      eax, ecx
003C6383  je       0x3c639c
003C6385  cmp      dword ptr [eax + 0x20], 0
003C6389  jne      0x3c639c
003C638B  lea      edx, [esp + 4]
003C638F  push     edx
003C6390  mov      ecx, esi
003C6392  call     0x26e930
003C6397  mov      eax, dword ptr [eax]
003C6399  pop      esi
003C639A  pop      ecx
```
