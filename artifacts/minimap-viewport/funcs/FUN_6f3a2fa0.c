

undefined4 __thiscall FUN_6f3a2fa0(int *param_1,int param_2)

{
  int iVar1;
  undefined4 uVar2;
  undefined **ppuStack_2c;
  int iStack_28;
  undefined4 uStack_24;
  int iStack_20;
  int iStack_1c;
  float fStack_18;
  float fStack_14;
  void *pvStack_10;
  undefined *puStack_c;
  int iStack_8;
  
  iStack_8 = 0xffffffff;
  puStack_c = &DAT_6f8e0808;
  pvStack_10 = ExceptionList;
  ExceptionList = &pvStack_10;
  iVar1 = FUN_6f09ba40(param_2,DAT_6fb6a774 ^ (uint)&stack0xfffffffc);
  if (iVar1 != 0) {
    ExceptionList = pvStack_10;
    return 1;
  }
  if (param_1[0x183] != 0) {
    FUN_6f34f3a0();
    FUN_6f34da20();
    iStack_28 = FUN_6f343250();
    if (iStack_28 == 0) {
      uStack_24 = 0x10065;
      ppuStack_2c = CMinimapDragEvent::vftable;
      fStack_18 = (float)param_1[0x1ce] * *(float *)(param_2 + 0x28) +
                  (float)param_1[0x1cb] * *(float *)(param_2 + 0x24) + (float)param_1[0x1d1];
      fStack_14 = (float)param_1[0x1cc] * *(float *)(param_2 + 0x24) +
                  (float)param_1[0x1cf] * *(float *)(param_2 + 0x28) + (float)param_1[0x1d2];
      iStack_1c = param_1[0x183];
      iStack_20 = iStack_28;
      iStack_8 = iStack_28;
      uVar2 = (**(code **)(*param_1 + 0x10))(&ppuStack_2c);
      ExceptionList = pvStack_10;
      return uVar2;
    }
  }
  ExceptionList = pvStack_10;
  return 0;
}


