

undefined4 __fastcall FUN_6f343250(int param_1)

{
  int iVar1;
  int iVar2;
  
  if (*(int *)(param_1 + 0x44) != 0) {
    iVar1 = FUN_6f037350();
    if (iVar1 != 0) {
      iVar2 = 0;
      if (*(int *)(iVar1 + 0xc) == 0x2b61676c) {
        iVar2 = iVar1;
      }
      if ((iVar2 != 0) && (*(int *)(iVar2 + 0x20) == 0)) {
        return 1;
      }
    }
  }
  return 0;
}


