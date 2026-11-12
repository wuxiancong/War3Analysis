

void __fastcall FUN_6f34f3a0(int param_1,int param_2)

{
  int iVar1;
  void *pvStack_10;
  undefined *puStack_c;
  undefined4 uStack_8;
  
  uStack_8 = 0xffffffff;
  puStack_c = &DAT_6f8da071;
  pvStack_10 = ExceptionList;
  ExceptionList = &pvStack_10;
  if ((DAT_6fbe6350 == 0) && (param_1 != 0)) {
    iVar1 = Ordinal_401(0x454,&DAT_6f98c4f8,0x1aaf,0,DAT_6fb6a774 ^ (uint)&stack0xfffffffc);
    uStack_8 = 0;
    if (iVar1 != 0) {
      FUN_6f349fa0();
    }
  }
  if (param_2 != 0) {
    DAT_6fbe6350 = 0;
  }
  ExceptionList = pvStack_10;
  return;
}


