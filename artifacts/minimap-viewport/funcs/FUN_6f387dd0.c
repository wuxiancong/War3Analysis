

void __fastcall FUN_6f387dd0(undefined4 *param_1)

{
  uint uVar1;
  int iVar2;
  void *pvStack_10;
  undefined *puStack_c;
  undefined4 uStack_8;
  
  puStack_c = &DAT_6f8defd2;
  pvStack_10 = ExceptionList;
  uVar1 = DAT_6fb6a774 ^ (uint)&stack0xfffffffc;
  ExceptionList = &pvStack_10;
  *param_1 = CMinimap::vftable;
  param_1[0x2d] = CMinimap::vftable;
  uStack_8 = 0xd;
  FUN_6f3913b0(uVar1);
  uVar1 = 0;
  if (param_1[0x175] != 0) {
    iVar2 = 0;
    do {
      if (*(int *)(iVar2 + param_1[0x176]) != 0) {
        FUN_6f04f1a0();
        *(undefined4 *)(iVar2 + param_1[0x176]) = 0;
      }
      uVar1 = uVar1 + 1;
      iVar2 = iVar2 + 0x28;
    } while (uVar1 < (uint)param_1[0x175]);
  }
  if (param_1[0x17a] != 0) {
    iVar2 = 0;
    uVar1 = 0;
    do {
      if (*(int *)(iVar2 + param_1[0x17b]) != 0) {
        FUN_6f04f1a0();
        *(undefined4 *)(iVar2 + param_1[0x17b]) = 0;
      }
      uVar1 = uVar1 + 1;
      iVar2 = iVar2 + 0x28;
    } while (uVar1 < (uint)param_1[0x17a]);
  }
  uVar1 = 0;
  if (param_1[0x68] != 0) {
    do {
      if (*(int *)(param_1[0x69] + uVar1 * 4) != 0) {
        FUN_6f04f1a0();
      }
      *(undefined4 *)(param_1[0x69] + uVar1 * 4) = 0;
      uVar1 = uVar1 + 1;
    } while (uVar1 < (uint)param_1[0x68]);
  }
  uVar1 = 0;
  if (param_1[0x6c] != 0) {
    do {
      if (*(int *)(param_1[0x6d] + uVar1 * 4) != 0) {
        FUN_6f04f1a0();
      }
      *(undefined4 *)(param_1[0x6d] + uVar1 * 4) = 0;
      uVar1 = uVar1 + 1;
    } while (uVar1 < (uint)param_1[0x6c]);
  }
  if (param_1[0x17f] != 0) {
    Ordinal_403(param_1[0x17f],s__I_6fb7b868,0xfffffffe,0);
  }
  if (param_1[0x17b] != 0) {
    Ordinal_403(param_1[0x17b],s___AUPing___6fb8df0c,0xfffffffe,0);
  }
  if (param_1[0x176] != 0) {
    Ordinal_403(param_1[0x176],s___AUPing___6fb8df0c,0xfffffffe,0);
  }
  if (param_1[0x171] != 0) {
    Ordinal_403(param_1[0x171],s___AVC3Vector_NTempest___6fb7df54,0xfffffffe,0);
  }
  uStack_8._0_1_ = 8;
  FUN_6f771b16(param_1 + 0x120,0x10,0x10,FUN_6f0d4ec0);
  uStack_8 = CONCAT31(uStack_8._1_3_,7);
  FUN_6f771b16(param_1 + 0xbd,0x10,0x11,FUN_6f0d4ec0);
  if (param_1[0xbc] != 0) {
    Ordinal_403(param_1[0xbc],s__I_6fb7b868,0xfffffffe,0);
  }
  if (param_1[0xb9] != 0) {
    Ordinal_403(param_1[0xb9],s__I_6fb7b868,0xfffffffe,0);
  }
  if (param_1[0xaf] != 0) {
    Ordinal_403(param_1[0xaf],s___AVC3Vector_NTempest___6fb7df54,0xfffffffe,0);
  }
  if (param_1[0xa3] != 0) {
    Ordinal_403(param_1[0xa3],s___AVC3Vector_NTempest___6fb7df54,0xfffffffe,0);
  }
  uStack_8 = CONCAT31(uStack_8._1_3_,2);
  FUN_6f050a40();
  if (param_1[0x6d] != 0) {
    Ordinal_403(param_1[0x6d],s__PAUHSPRITEBASE_____6fb7d040,0xfffffffe,0);
  }
  if (param_1[0x69] != 0) {
    Ordinal_403(param_1[0x69],s__PAUHSPRITEBASE_____6fb7d040,0xfffffffe,0);
  }
  uStack_8 = 0xffffffff;
  FUN_6f0a0f00();
  ExceptionList = pvStack_10;
  return;
}


  from 6f382178 DATA in FUN_6f382140@6f382140

