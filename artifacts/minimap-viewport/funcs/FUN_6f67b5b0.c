

void __thiscall FUN_6f67b5b0(int *param_1,uint param_2,int param_3,int param_4)

{
  uint uVar1;
  short sVar2;
  undefined2 uVar3;
  undefined4 uVar4;
  int *piVar5;
  int iVar6;
  int iVar7;
  uint uVar8;
  undefined4 *puVar9;
  undefined4 uVar10;
  undefined4 uVar11;
  undefined4 uVar12;
  undefined4 uVar13;
  undefined **ppuStack_4c;
  undefined4 uStack_48;
  undefined4 uStack_44;
  int *piStack_40;
  uint uStack_3c;
  uint uStack_38;
  undefined1 auStack_34 [4];
  undefined4 uStack_30;
  undefined4 uStack_2c;
  undefined4 uStack_28;
  uint uStack_24;
  int iStack_20;
  int iStack_1c;
  int iStack_18;
  uint uStack_14;
  void *pvStack_10;
  undefined *puStack_c;
  undefined4 uStack_8;
  
  uVar8 = param_2;
  uStack_8 = 0xffffffff;
  puStack_c = &DAT_6f92ade8;
  pvStack_10 = ExceptionList;
  ExceptionList = &pvStack_10;
  uVar1 = param_1[0x16];
  if (param_2 != uVar1) {
    iStack_20 = DAT_6fbe4238;
    uStack_24 = uVar1;
    uStack_28 = FUN_6f1c3200(DAT_6fb6a774 ^ (uint)&stack0xfffffffc);
    uStack_14 = FUN_6f1c3330(uVar1);
    iStack_18 = FUN_6f1c3330(uVar8);
    FUN_6f03f7a0(*(int *)(iStack_18 + 0x268) == 0);
    (**(code **)(*param_1 + 0x98))();
    if (((*(byte *)(param_1 + 8) & 1) == 0) && ((param_1[0x17] & 0x100U) == 0)) {
      uVar12 = 1;
      uVar10 = 1;
      uVar4 = FUN_6f673200(0);
      FUN_6f662bf0(uVar4,uVar10,uVar12);
    }
    else {
      FUN_6f656750();
    }
    iVar6 = param_1[0xc];
    iStack_1c = iVar6;
    if ((param_1[0x19] & 8U) == 0) {
      if ((param_1[0x19] & 0x10U) != 0) {
        FUN_6f249350(iVar6);
      }
    }
    else {
      FUN_6f23e630(iVar6,0);
    }
    if ((param_1[0x19] & 1U) == 0) {
      if ((param_1[0x19] & 2U) != 0) {
        FUN_6f23ddd0(iVar6,0);
      }
    }
    else {
      FUN_6f24d520(iVar6,0);
    }
    uVar13 = 1;
    uVar11 = 1;
    uVar12 = 0;
    uVar10 = 1;
    uVar4 = FUN_6f61be20(1,0,1,1);
    piVar5 = (int *)FUN_6f46f440(uVar4,uVar10,uVar12,uVar11,uVar13);
    if ((piVar5 != (int *)0x0) && (iVar6 = (**(code **)(*piVar5 + 0x368))(), iVar6 != 0)) {
      iStack_1c = piVar5[0x38];
    }
    if ((param_1[0x19] & 0x800U) != 0) {
      iVar6 = FUN_6f662900();
      iVar7 = FUN_6f039860();
      FUN_6f039900(iVar7 - iVar6);
      uVar1 = *(uint *)(uStack_14 + 0x248);
      uVar8 = FUN_6f039860();
      if (uVar1 < uVar8) {
        *(uint *)(uStack_14 + 0x248) = uVar8;
      }
    }
    if ((param_1[0x19] & 0x200U) != 0) {
      iVar6 = FUN_6f662960();
      FUN_6f23dac0(-iVar6);
    }
    if ((param_1[0x19] & 0x100U) != 0) {
      uVar4 = FUN_6f662960();
      FUN_6f23dac0(uVar4);
    }
    if ((param_1[0x19] & 0x400U) != 0) {
      iVar6 = FUN_6f662900();
      iVar7 = FUN_6f039860();
      FUN_6f039900(iVar7 + iVar6);
      uVar1 = *(uint *)(iStack_18 + 0x248);
      uVar8 = FUN_6f039860();
      if (uVar1 < uVar8) {
        *(uint *)(iStack_18 + 0x248) = uVar8;
      }
    }
    FUN_6f6ad4e0();
    uStack_14 = (uint)*(ushort *)(iStack_20 + 0x28);
    if (uStack_24 == uStack_14) {
      if ((*(byte *)(param_1 + 0x92) & 0x10) != 0) {
        FUN_6f67ff30(1);
      }
      if ((*(byte *)(param_1 + 0x92) & 0x40) != 0) {
        FUN_6f680380(1);
      }
    }
    iVar6 = FUN_6f039860();
    if (iVar6 == 0) {
      puVar9 = (undefined4 *)FUN_6f64d660(auStack_34);
    }
    else {
      puVar9 = (undefined4 *)FUN_6f64d6f0(&uStack_28);
    }
    uVar1 = param_2;
    uStack_2c = *puVar9;
    if (param_4 != 0) {
      FUN_6f66b670(iStack_1c);
    }
    param_1[0x16] = uVar1;
    FUN_6f03ee00(uVar1);
    FUN_6f03f620(uVar1);
    FUN_6f676620();
    FUN_6f6aa8e0();
    if (iVar6 == 0) {
      puVar9 = (undefined4 *)FUN_6f64d660(&param_4);
    }
    else {
      puVar9 = (undefined4 *)FUN_6f64d6f0(&param_2);
    }
    uStack_30 = *puVar9;
    uVar4 = FUN_6f0528b0(&uStack_2c);
    FUN_6f653170(uVar4);
    param_2 = (uint)(uVar1 == uStack_14);
    param_4 = FUN_6f1ccf30(uVar1,uStack_14);
    if ((((uint)param_1[0xc] >> 0x18) - 0x41 < 0x1a) && ((param_1[0x17] & 0x40000000U) == 0)) {
      FUN_6f67fa80(0);
    }
    if (param_2 == 0) {
      FUN_6f358c10();
      FUN_6f358af0();
      FUN_6f358c30(0xb6);
    }
    else {
      iVar6 = FUN_6f66e5f0();
      if (iVar6 != 0) {
        FUN_6f67ff30(0);
      }
      if ((*(byte *)(param_1 + 0x92) & 0x40) != 0) {
        FUN_6f680380(0);
      }
    }
    sVar2 = FUN_6f2412c0();
    if (sVar2 != 0) {
      uVar3 = FUN_6f2412c0();
      FUN_6f6781a0(uVar3);
    }
    iVar6 = FUN_6f668e40();
    if ((iVar6 == 10) && (param_1[0x16] == 0xf)) {
      param_1[0x17] = param_1[0x17] | 0x80000;
    }
    else {
      param_1[0x17] = param_1[0x17] & 0xfff7ffff;
    }
    if ((((param_1[0x17] & 0x1000000U) != 0) || ((param_1[8] & 0x4000000U) != 0)) ||
       ((param_1[0x18] & 0x800U) != 0)) {
      FUN_6f67fb00();
    }
    if ((param_1[0x17] & 0x40000000U) != 0) {
      (**(code **)(*param_1 + 0xb4))();
    }
    iVar6 = FUN_6f66ea60(1);
    if (((iVar6 != 0) && ((iVar6 = param_1[0x16], iVar6 == 0xf || (iVar6 == 0xc)))) &&
       ((param_1[0x92] & 0x100U) != 0)) {
      if (iVar6 == 0xf) {
        param_1[0x17] = param_1[0x17] | 0x40000;
      }
      else {
        param_1[0x17] = param_1[0x17] & 0xfffbffff;
      }
    }
    if (param_3 != 0) {
      FUN_6f6a1230(uVar1);
    }
    if ((param_2 == 0) && (param_4 == 0)) {
      (**(code **)(*param_1 + 0x1cc))(0xffff,0);
    }
    iVar6 = FUN_6f1c3330(*(undefined2 *)(iStack_20 + 0x28));
    if ((iVar6 != 0) && (iVar7 = FUN_6f272c50(param_1), iVar7 != 0)) {
      (**(code **)(*param_1 + 0x194))(1,0,1,0,*(undefined1 *)(iVar6 + 0x30));
    }
    uVar8 = uStack_24;
    FUN_6f65dcd0(uStack_24);
    uStack_48 = 0;
    uStack_44 = 0xd01a2;
    ppuStack_4c = CEventOwnerChange::vftable;
    uStack_3c = uVar8;
    uStack_38 = uVar1;
    uStack_8 = 0;
    piStack_40 = param_1;
    (**(code **)(*param_1 + 0x10))(&ppuStack_4c);
    FUN_6f633980();
    FUN_6f6608c0(0);
    param_1[0x17] = param_1[0x17] & 0xfffffffb;
    FUN_6f88e130();
    FUN_6f676670();
    FUN_6f676610(1);
    FUN_6f3598e0();
    FUN_6f3593d0();
    FUN_6f6374a0();
  }
  ExceptionList = pvStack_10;
  return;
}


