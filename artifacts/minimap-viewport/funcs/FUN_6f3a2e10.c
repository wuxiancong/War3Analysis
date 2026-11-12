

int __thiscall FUN_6f3a2e10(int *param_1,int param_2)

{
  float fVar1;
  float fVar2;
  float fVar3;
  float fVar4;
  float fVar5;
  int iVar6;
  undefined1 auStack_30 [16];
  undefined4 uStack_20;
  float fStack_1c;
  float fStack_18;
  float fStack_14;
  void *pvStack_10;
  undefined *puStack_c;
  undefined4 uStack_8;
  
  uStack_8 = 0xffffffff;
  puStack_c = &DAT_6f8e07d8;
  pvStack_10 = ExceptionList;
  ExceptionList = &pvStack_10;
  iVar6 = FUN_6f09ba20(param_2,DAT_6fb6a774 ^ (uint)&stack0xfffffffc);
  if (iVar6 != 0) {
    ExceptionList = pvStack_10;
    return 1;
  }
  if ((param_1[0x182] & *(uint *)(param_2 + 0x14)) != 0) {
    param_1[0x183] = *(uint *)(param_2 + 0x14);
    FUN_6f0bc8d0(1);
  }
  iVar6 = FUN_6f0566d0(0x10064);
  if ((iVar6 != 0) && ((*(uint *)(param_2 + 0x14) & param_1[0x181]) != 0)) {
    FUN_6f34f3a0();
    FUN_6f34da20();
    iVar6 = FUN_6f343250();
    if (iVar6 == 0) {
      fVar1 = (float)param_1[0x1ce];
      fVar2 = *(float *)(param_2 + 0x28);
      fVar3 = (float)param_1[0x1cb];
      fVar4 = *(float *)(param_2 + 0x24);
      fVar5 = (float)param_1[0x1d1];
      fStack_14 = (float)param_1[0x1cc] * *(float *)(param_2 + 0x24) +
                  (float)param_1[0x1cf] * *(float *)(param_2 + 0x28) + (float)param_1[0x1d2];
      FUN_6f383100();
      uStack_20 = *(undefined4 *)(param_2 + 0x14);
      uStack_8 = 0;
      fStack_18 = fStack_14;
      fStack_1c = fVar1 * fVar2 + fVar3 * fVar4 + fVar5;
      iVar6 = (**(code **)(*param_1 + 0x10))(auStack_30);
      if (iVar6 == 1) {
        param_1[0x183] = 0;
        FUN_6f0bc8d0(0);
      }
      ExceptionList = pvStack_10;
      return iVar6;
    }
  }
  ExceptionList = pvStack_10;
  return 0;
}


