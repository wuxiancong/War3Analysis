

void __fastcall FUN_6f349fa0(undefined4 *param_1)

{
  int *piVar1;
  int *piVar2;
  undefined4 *puVar3;
  undefined4 uVar4;
  int iVar5;
  undefined4 uVar6;
  int *piVar7;
  undefined4 *puVar8;
  float10 fVar9;
  float fVar10;
  undefined4 uVar11;
  undefined4 uVar12;
  undefined4 uVar13;
  undefined4 uStack_154;
  undefined4 uStack_150;
  int *piStack_14c;
  undefined4 *puStack_148;
  undefined4 uStack_120;
  undefined1 auStack_118 [260];
  uint uStack_14;
  void *pvStack_10;
  undefined *puStack_c;
  undefined4 uStack_8;
  
  uStack_8 = 0xffffffff;
  puStack_c = &DAT_6f8d950e;
  pvStack_10 = ExceptionList;
  uStack_14 = DAT_6fb6a774 ^ (uint)&stack0xfffffffc;
  ExceptionList = &pvStack_10;
  FUN_6f0c9bf0(uStack_14);
  uStack_8 = 0;
  *param_1 = CGameUI::vftable;
  param_1[0x2d] = CGameUI::vftable;
  param_1[0x60] = 0;
  FUN_6f349df0();
  param_1[0x6b] = 1;
  param_1[0x6c] = 1;
  param_1[0x6d] = 0;
  param_1[0x6e] = 0;
  param_1[0x6f] = 0;
  param_1[0x70] = 0;
  param_1[0x71] = 0;
  param_1[0x72] = 0;
  param_1[0x73] = 0;
  param_1[0x74] = 1;
  param_1[0x75] = 0;
  param_1[0x76] = 0;
  param_1[0x77] = 1;
  param_1[0x78] = 0;
  param_1[0x79] = 0;
  param_1[0x7a] = 0;
  param_1[0x7b] = 0;
  param_1[0x7c] = 0;
  param_1[0x7d] = 0;
  param_1[0x7e] = 0;
  param_1[0x7f] = 0;
  param_1[0x80] = 0;
  param_1[0x81] = 0;
  param_1[0x82] = 0;
  param_1[0x83] = 0;
  param_1[0x84] = 0;
  param_1[0x85] = 0;
  param_1[0x88] = 0;
  param_1[0x89] = 0;
  param_1[0x8a] = 0;
  param_1[0x8b] = 0;
  param_1[0x8c] = 0;
  param_1[0x8d] = 0;
  param_1[0x8e] = 0;
  param_1[0x8f] = 0;
  param_1[0x90] = 0;
  param_1[0x91] = 0;
  param_1[0x92] = 0;
  param_1[0x95] = 0;
  uStack_8._0_1_ = 0x10;
  param_1[0x96] = 0;
  param_1[0x97] = 0;
  param_1[0x98] = 0;
  param_1[0x99] = 0;
  param_1[0x9a] = 0;
  param_1[0x9b] = 0;
  param_1[0x9c] = 0;
  param_1[0x9d] = 0;
  param_1[0x9e] = 0;
  param_1[0x9f] = 0;
  param_1[0xa0] = 0;
  param_1[0xa1] = 0;
  param_1[0xa2] = 0;
  param_1[0xa3] = 0;
  param_1[0xa4] = 1;
  param_1[0xa5] = 1;
  param_1[0xa6] = 1;
  param_1[0xa7] = 1;
  param_1[0xa8] = 1;
  param_1[0xa9] = 1;
  FUN_6f318130();
  uStack_8._0_1_ = 0x11;
  FUN_6f318130();
  uStack_8._0_1_ = 0x12;
  FUN_6f318130();
  param_1[0xde] = 0;
  param_1[0xdf] = 0;
  param_1[0xe0] = 0;
  param_1[0xe2] = 0;
  param_1[0xe1] = CAgentTimer::vftable;
  param_1[0xe3] = 0;
  param_1[0xe4] = 0;
  param_1[0xe5] = 0;
  param_1[0xe6] = 0;
  param_1[0xe7] = 0;
  param_1[0xe8] = 0;
  param_1[0xe9] = 0;
  param_1[0xea] = 0;
  param_1[0xeb] = 0;
  param_1[0xec] = 0;
  param_1[0xed] = 0;
  param_1[0xee] = 0;
  param_1[0xf2] = 0;
  param_1[0xf6] = 0;
  param_1[0xff] = 0;
  uStack_8._0_1_ = 0x1e;
  param_1[0x101] = 0;
  DAT_6fbe6350 = param_1;
  FUN_6f090bd0();
  FUN_6f090c90();
  piStack_14c = (int *)Ordinal_401(0x668,&DAT_6f98c4f8,0x120,0);
  uStack_8._0_1_ = 0x1f;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f35efb0(param_1);
  }
  uStack_8 = CONCAT31(uStack_8._1_3_,0x1e);
  param_1[0xef] = uVar4;
  FUN_6f343180();
  iVar5 = FUN_6f0219f0();
  uVar4 = *(undefined4 *)(iVar5 + 0x70);
  FUN_6f343180(uVar4);
  FUN_6f038b20(uVar4);
  uStack_120 = 0xfffffffe;
  iVar5 = FUN_6f1012b0(1);
  piStack_14c = *(int **)(iVar5 + 0x54);
  if (piStack_14c != (int *)0x0) {
    FUN_6f343180();
    (**(code **)(*piStack_14c + 0x1c))();
    iVar5 = FUN_6f02fbf0();
    piVar7 = piStack_14c;
    if (iVar5 != 0) goto LAB_6f34a3d5;
  }
  piVar7 = (int *)0x0;
LAB_6f34a3d5:
  piVar2 = (int *)param_1[0x95];
  if (piVar2 != piVar7) {
    if (piVar2 != (int *)0x0) {
      piVar1 = piVar2 + 1;
      *piVar1 = *piVar1 + -1;
      if (*piVar1 == 0) {
        (**(code **)*piVar2)();
      }
    }
    if ((piVar7 != (int *)0x0) && (piStack_14c != (int *)0x0)) {
      piStack_14c[1] = piStack_14c[1] + 1;
    }
    param_1[0x95] = piVar7;
  }
  FUN_6f343460();
  uVar4 = FUN_6f02a380(0);
  param_1[0x10b] = uVar4;
  uVar4 = FUN_6f02a380(0);
  param_1[0x10c] = uVar4;
  uVar4 = FUN_6f02a380(0);
  param_1[0x10d] = uVar4;
  uVar4 = FUN_6f02a380(0);
  param_1[0x10e] = uVar4;
  uVar4 = FUN_6f02a380(0);
  param_1[0x10f] = uVar4;
  uVar4 = FUN_6f02a380(0);
  param_1[0x110] = uVar4;
  uVar4 = FUN_6f02a380(0);
  param_1[0x111] = uVar4;
  uVar4 = FUN_6f02a380(0);
  param_1[0x112] = uVar4;
  uVar4 = FUN_6f02a380(0);
  param_1[0x113] = uVar4;
  uVar4 = FUN_6f02a380(0);
  param_1[0x114] = uVar4;
  FUN_6f056af0(0x40060064,0x40060064,param_1);
  FUN_6f056af0(0x40060066,0x40060066,param_1);
  FUN_6f056af0(0x40060065,0x40060065,param_1);
  FUN_6f056af0(0x40060067,0x40060067,param_1);
  FUN_6f056af0(0x400500c8,0x400500c8,param_1);
  FUN_6f056af0(0x40040065,0x40040065,param_1);
  FUN_6f057a90(param_1,0x40000000);
  FUN_6f30ee00(param_1,0);
  FUN_6f30ed80(param_1,0);
  FUN_6f30ed80(param_1,0);
  FUN_6f30ed80(param_1,0);
  FUN_6f30ed80(param_1,0);
  FUN_6f30ed80(param_1,0);
  FUN_6f30ed80(param_1,1);
  FUN_6f30ed80(param_1,1);
  FUN_6f30eda0(param_1,0);
  FUN_6f30eda0(param_1,0);
  FUN_6f30eda0(param_1,0);
  FUN_6f30eda0(param_1,0);
  FUN_6f30eda0(param_1,0);
  FUN_6f30eda0(param_1,0);
  FUN_6f30eda0(param_1,0);
  FUN_6f30eda0(param_1,0);
  FUN_6f30eda0(param_1,0);
  FUN_6f30eda0(param_1,0);
  FUN_6f30eda0(param_1,0);
  iVar5 = FUN_6f30e2d0();
  if (iVar5 == 0x424e4554) {
    FUN_6f30eda0(param_1,0);
  }
  uVar4 = FUN_6f1850d0();
  uVar13 = 0;
  uVar12 = 0;
  uVar11 = 0;
  uVar6 = FUN_6f33e550(0,0,0);
  FUN_6f324ad0(uVar6);
  FUN_6f186a90(uVar6,uVar11,uVar12,uVar13);
  piStack_14c = (int *)0x0;
  FUN_6f186590(1,0);
  FUN_6f09cd10(uVar4);
  FUN_6f04f1a0();
  puVar8 = param_1 + 0x2d;
  FUN_6f0bd8a0(6,puVar8,6,0,0x3e051eb8,1);
  FUN_6f0bd8a0(2,puVar8,2,0,0xbca3d70a,1);
  iVar5 = FUN_6f0a1760(0);
  param_1[0x109] = iVar5;
  *(uint *)(iVar5 + 0xc) = *(uint *)(iVar5 + 0xc) | *(uint *)(iVar5 + 0x10) | 0x12;
  FUN_6f0bd750(puVar8,1);
  piStack_14c = (int *)Ordinal_401(0x264,&DAT_6f98c4f8,0x172,0);
  uStack_8._0_1_ = 0x20;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
    puStack_148 = piStack_14c;
  }
  else {
    puStack_148 = piStack_14c;
    uVar4 = FUN_6f3835c0(param_1[0x109]);
  }
  uStack_8._0_1_ = 0x1e;
  param_1[0xfd] = uVar4;
  FUN_6f0bea20(5);
  FUN_6f0bf020(0x1f,param_1,1);
  piStack_14c = (int *)Ordinal_401(0x8fc,&DAT_6f98c4f8,0x176,0);
  uStack_8._0_1_ = 0x21;
  puStack_148 = piStack_14c;
  if (piStack_14c != (int *)0x0) {
    FUN_6f0b6a00(param_1,0,0);
  }
  uStack_8 = CONCAT31(uStack_8._1_3_,0x1e);
  FUN_6f0bd750(puVar8,1);
  uVar4 = 0;
  FUN_6f324ad0(0);
  piVar7 = (int *)FUN_6f090a60(uVar4);
  param_1[0x10a] = piVar7;
  piStack_14c = (int *)piVar7[0x21];
  puStack_148 = (undefined4 *)piVar7[0x25];
  if (puStack_148 != (undefined4 *)0x0) {
    piVar7[0x24] = 0;
    (**(code **)(*piVar7 + 100))();
  }
  piVar7[0x21] = (int)piStack_14c + 1;
  if (puStack_148 != (undefined4 *)0x0) {
    piVar7[0x24] = 1;
    (**(code **)(*piVar7 + 0x68))();
  }
  puVar8 = param_1 + 0x2d;
  FUN_6f0bd750(puVar8,1);
  piStack_14c = (int *)Ordinal_401(0x134,&DAT_6f98c4f8,0x17f,0);
  uStack_8._0_1_ = 0x22;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f383f10(0);
  }
  uStack_8._0_1_ = 0x1e;
  param_1[0x108] = uVar4;
  FUN_6f0bd750(puVar8,1);
  iVar5 = FUN_6f0a1760(0);
  param_1[0x107] = iVar5;
  *(uint *)(iVar5 + 0xc) = *(uint *)(iVar5 + 0xc) | *(uint *)(iVar5 + 0x10) | 0x12;
  FUN_6f0bd750(puVar8,1);
  piStack_14c = (int *)Ordinal_401(0x1c0,&DAT_6f98c4f8,0x188,0);
  uStack_8._0_1_ = 0x23;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f3844e0(param_1[0x107]);
  }
  param_1[0xfe] = uVar4;
  piStack_14c = (int *)Ordinal_401(0x170,&DAT_6f98c4f8,0x18a,0);
  uStack_8._0_1_ = 0x24;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f318330(0,0xff);
  }
  param_1[0xdd] = uVar4;
  piStack_14c = (int *)Ordinal_401(0x818,&DAT_6f98c4f8,0x18c,0);
  uStack_8._0_1_ = 0x25;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f382140(param_1);
  }
  uStack_8._0_1_ = 0x1e;
  param_1[0xf0] = uVar4;
  if (param_1[0x107] == 0) {
    iVar5 = 0;
  }
  else {
    iVar5 = param_1[0x107] + 0xb4;
  }
  FUN_6f0bd8a0(6,iVar5,6,0x3c19999a,0x3be147ae,1);
  if (param_1[0x107] == 0) {
    iVar5 = 0;
  }
  else {
    iVar5 = param_1[0x107] + 0xb4;
  }
  FUN_6f0bd8a0(2,iVar5,6,0x3e1851ec,0x3e147ae1,1);
  *(undefined4 *)(param_1[0xf0] + 0x604) = 5;
  *(undefined4 *)(param_1[0xf0] + 0x608) = 1;
  (**(code **)(*(int *)param_1[0xf0] + 8))(0x10064,0x10064,param_1);
  (**(code **)(*(int *)param_1[0xf0] + 8))(0x10065,0x10065,param_1);
  FUN_6f350110();
  FUN_6f36d590(param_1[0xf0]);
  iVar5 = FUN_6f30e9a0();
  if (iVar5 == 0) {
    piStack_14c = (int *)Ordinal_401(0x168,&DAT_6f98c4f8,0x199,0);
    uStack_8._0_1_ = 0x26;
    puStack_148 = piStack_14c;
    if (piStack_14c == (int *)0x0) {
      uVar4 = 0;
    }
    else {
      uVar4 = FUN_6f0bb2a0(param_1[0x10a]);
    }
    uStack_8._0_1_ = 0x1e;
    param_1[0xf6] = uVar4;
    FUN_6f0bd960(0x3e32b021);
    FUN_6f0bd7c0(0x3e22d0e6);
    FUN_6f0bd8a0(8,param_1[0x10a],8,0xbbf1a9fc,0x3b03126f,1);
    FUN_6f0bb8d0(0x50);
    FUN_6f0bb810(0x20,param_1);
  }
  else {
    param_1[0xf6] = 0;
  }
  piStack_14c = (int *)Ordinal_401(0x1c0,&DAT_6f98c4f8,0x1a3,0);
  uStack_8._0_1_ = 0x27;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f37fc80(param_1[0x10a]);
  }
  param_1[0xf2] = uVar4;
  piStack_14c = (int *)Ordinal_401(0x154,&DAT_6f98c4f8,0x1a4,0);
  uStack_8._0_1_ = 0x28;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f380f40(param_1[0x10a]);
  }
  uStack_8._0_1_ = 0x1e;
  param_1[0xf1] = uVar4;
  uVar4 = FUN_6f090a60(0);
  param_1[0xf3] = uVar4;
  FUN_6f0bd8a0(2,puVar8,2,0,0,1);
  uVar4 = FUN_6f090a60(0);
  param_1[0xf4] = uVar4;
  FUN_6f0bd8a0(0,puVar8,0,0,0,1);
  piStack_14c = (int *)Ordinal_401(0x184,&DAT_6f98c4f8,0x1cc,0);
  uStack_8._0_1_ = 0x29;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f380980(param_1[0x10a]);
  }
  uStack_8._0_1_ = 0x1e;
  param_1[0xf7] = uVar4;
  FUN_6f0bd8a0(0,puVar8,0,0x3b75c28f,0xbcd70a3d,1);
  piStack_14c = (int *)Ordinal_401(0x154,&DAT_6f98c4f8,0x1cf,0);
  uStack_8._0_1_ = 0x2a;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f383400(param_1[0x10a]);
  }
  uStack_8._0_1_ = 0x1e;
  param_1[0xf8] = uVar4;
  FUN_6f0bd8a0(6,puVar8,6,0x3b75c28f,0x3e2e147b,1);
  piStack_14c = (int *)Ordinal_401(0x1ec,&DAT_6f98c198,0x46,0);
  uStack_8._0_1_ = 0x2b;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    iVar5 = 0;
  }
  else {
    iVar5 = FUN_6f37f380(param_1,0,0x2422);
  }
  uStack_8._0_1_ = 0x1e;
  if (iVar5 != 0) {
    *(int *)(iVar5 + 4) = *(int *)(iVar5 + 4) + 1;
  }
  puVar3 = (undefined4 *)param_1[0xff];
  piStack_14c = (int *)iVar5;
  if (puVar3 != (undefined4 *)0x0) {
    piVar7 = puVar3 + 1;
    *piVar7 = *piVar7 + -1;
    if (*piVar7 == 0) {
      (**(code **)*puVar3)();
    }
  }
  param_1[0xff] = piStack_14c;
  FUN_6f0bd7c0(0x3cf5c28f);
  if (param_1[0x107] == 0) {
    iVar5 = 0;
  }
  else {
    iVar5 = param_1[0x107] + 0xb4;
  }
  FUN_6f0bd8a0(3,iVar5,6,0x3e4ccccd,DAT_6fb6990c,1);
  if (param_1[0x107] == 0) {
    iVar5 = 0;
  }
  else {
    iVar5 = param_1[0x107] + 0xb4;
  }
  FUN_6f0bd8a0(5,iVar5,8,0xbe4ccccd,DAT_6fb6990c,1);
  FUN_6f392060(0);
  FUN_6f3acbe0(0,param_1,1);
  piStack_14c = (int *)Ordinal_401(0x100,&DAT_6f98c4f8,0x1da,0);
  uStack_8._0_1_ = 0x2c;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f371aa0(param_1[0xef]);
  }
  param_1[0x93] = uVar4;
  piStack_14c = (int *)Ordinal_401(0x8c,&DAT_6f98c4f8,0x1db,0);
  uStack_8._0_1_ = 0x2d;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f371660();
  }
  param_1[0x94] = uVar4;
  piStack_14c = (int *)Ordinal_401(0x194,&DAT_6f98c4f8,0x1dd,0);
  uStack_8._0_1_ = 0x2e;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f0c1ac0(0);
  }
  param_1[0xf9] = uVar4;
  uStack_8._0_1_ = 0x1e;
  fVar9 = (float10)FUN_6f02a2f0(0);
  uVar6 = 1;
  fVar10 = (float)fVar9;
  puStack_148 = (undefined4 *)fVar10;
  uVar4 = FUN_6f324ad0(fVar10,1);
  FUN_6f0c2e80(uVar4,fVar10,uVar6);
  FUN_6f0bd960(0x3ec28f5c);
  FUN_6f0bd7c0(0x3d4ccccd);
  FUN_6f0bd8a0(7,param_1[0x10a],7,0,0x3e3851ec,1);
  uStack_150 = 0x3a83126f;
  piStack_14c = (int *)0xba83126f;
  FUN_6f0c2200(0xff000000,&uStack_150);
  piStack_14c = (int *)Ordinal_401(0x194,&DAT_6f98c4f8,0x1e4,0);
  uStack_8._0_1_ = 0x2f;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f0c1ac0(0);
  }
  param_1[0xfc] = uVar4;
  uStack_8._0_1_ = 0x1e;
  fVar9 = (float10)FUN_6f02a2f0(0);
  uVar6 = 1;
  fVar10 = (float)fVar9;
  puStack_148 = (undefined4 *)fVar10;
  uVar4 = FUN_6f324ad0(fVar10,1);
  FUN_6f0c2e80(uVar4,fVar10,uVar6);
  FUN_6f0c2f10(2);
  FUN_6f0bd960(0x3ec28f5c);
  FUN_6f0bd7c0(0x3d4ccccd);
  FUN_6f0bd8a0(1,param_1[0x10a],1,0,0xbcd4fdf4,1);
  uStack_150 = 0x3a83126f;
  piStack_14c = (int *)0xba83126f;
  FUN_6f0c2200(0xff000000,&uStack_150);
  piStack_14c = (int *)Ordinal_401(0x194,&DAT_6f98c4f8,0x1ec,0);
  uStack_8._0_1_ = 0x30;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f0c1ac0(0);
  }
  param_1[0xfa] = uVar4;
  uStack_8._0_1_ = 0x1e;
  fVar9 = (float10)FUN_6f02a2f0(0);
  uVar6 = 1;
  fVar10 = (float)fVar9;
  puStack_148 = (undefined4 *)fVar10;
  uVar4 = FUN_6f324ad0(fVar10,1);
  FUN_6f0c2e80(uVar4,fVar10,uVar6);
  FUN_6f0bd960(0x3f000000);
  FUN_6f0bd7c0(0x3e800000);
  FUN_6f0bd8a0(7,param_1[0xf9],1,0xbdc8f5c3,0x3a03126f,1);
  uStack_150 = 0x3a83126f;
  piStack_14c = (int *)0xba83126f;
  FUN_6f0c2200(0xff000000,&uStack_150);
  FUN_6f2a1f40();
  piStack_14c = (int *)Ordinal_401(0x194,&DAT_6f98c4f8,0x1f5,0);
  uStack_8._0_1_ = 0x31;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    uVar4 = 0;
  }
  else {
    uVar4 = FUN_6f0c1ac0(0);
  }
  param_1[0xfb] = uVar4;
  uStack_8._0_1_ = 0x1e;
  fVar9 = (float10)FUN_6f02a2f0(0);
  puStack_148 = (undefined4 *)(float)fVar9;
  FUN_6f0c2e80(auStack_118,puStack_148,1);
  FUN_6f0c2fe0(0x9f);
  FUN_6f0bd8a0(1,puVar8,1,0,0,1);
  FUN_6f0bd8a0(7,param_1[0x10a],7,0,0x3e4ccccd,1);
  FUN_6f0bd8a0(3,param_1[0x10a],3,0x3bcccccd,0,1);
  FUN_6f0bd8a0(5,param_1[0x10a],5,0xbca3d70a,0,1);
  uStack_150 = 0x3a83126f;
  piStack_14c = (int *)0xba83126f;
  FUN_6f0c2200(0xff000000,&uStack_150);
  uVar4 = FUN_6f0909c0(0,0,0);
  param_1[0x100] = uVar4;
  FUN_6f0bd8a0(7,puVar8,7,0,0,1);
  FUN_6f09ca50(0,0);
  (**(code **)(*(int *)param_1[0x100] + 0xd0))();
  piStack_14c = (int *)Ordinal_401(0x34,&DAT_6f98c4f8,0x204,0);
  uStack_8._0_1_ = 0x32;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    iVar5 = 0;
  }
  else {
    iVar5 = FUN_6f371a30();
  }
  uStack_8._0_1_ = 0x1e;
  if (iVar5 != 0) {
    *(int *)(iVar5 + 4) = *(int *)(iVar5 + 4) + 1;
  }
  puVar8 = (undefined4 *)param_1[0x85];
  if (puVar8 != (undefined4 *)0x0) {
    piVar7 = puVar8 + 1;
    *piVar7 = *piVar7 + -1;
    if (*piVar7 == 0) {
      (**(code **)*puVar8)();
    }
  }
  param_1[0x85] = iVar5;
  piStack_14c = (int *)Ordinal_401(0x38,&DAT_6f98c4f8,0x205,0);
  uStack_8._0_1_ = 0x33;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    iVar5 = 0;
  }
  else {
    iVar5 = FUN_6f34b7d0();
  }
  uStack_8._0_1_ = 0x1e;
  if (iVar5 != 0) {
    *(int *)(iVar5 + 4) = *(int *)(iVar5 + 4) + 1;
  }
  puVar8 = (undefined4 *)param_1[0x84];
  if (puVar8 != (undefined4 *)0x0) {
    piVar7 = puVar8 + 1;
    *piVar7 = *piVar7 + -1;
    if (*piVar7 == 0) {
      (**(code **)*puVar8)();
    }
  }
  param_1[0x84] = iVar5;
  puVar8 = (undefined4 *)Ordinal_401(0xc,&DAT_6f98c4f8,0x206,0);
  uStack_8._0_1_ = 0x34;
  piStack_14c = puVar8;
  puStack_148 = puVar8;
  if (puVar8 == (undefined4 *)0x0) {
    puVar8 = (undefined4 *)0x0;
  }
  else {
    FUN_6f055c90();
    *puVar8 = CDragSelectMode::vftable;
  }
  param_1[0x86] = puVar8;
  puVar8 = (undefined4 *)Ordinal_401(0xc,&DAT_6f98c4f8,0x207,0);
  uStack_8._0_1_ = 0x35;
  piStack_14c = puVar8;
  puStack_148 = puVar8;
  if (puVar8 == (undefined4 *)0x0) {
    puVar8 = (undefined4 *)0x0;
  }
  else {
    FUN_6f055c90();
    *puVar8 = CDragScrollMode::vftable;
  }
  param_1[0x87] = puVar8;
  piStack_14c = (int *)Ordinal_401(0x14,&DAT_6f98c4f8,0x208,0);
  uStack_8._0_1_ = 0x36;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    iVar5 = 0;
  }
  else {
    iVar5 = FUN_6f3c29b0(param_1[0xef]);
  }
  uStack_8._0_1_ = 0x1e;
  if (iVar5 != 0) {
    *(int *)(iVar5 + 4) = *(int *)(iVar5 + 4) + 1;
  }
  puVar8 = (undefined4 *)param_1[0x88];
  if (puVar8 != (undefined4 *)0x0) {
    piVar7 = puVar8 + 1;
    *piVar7 = *piVar7 + -1;
    if (*piVar7 == 0) {
      (**(code **)*puVar8)();
    }
  }
  param_1[0x88] = iVar5;
  puVar8 = (undefined4 *)Ordinal_401(0xc,&DAT_6f98c4f8,0x209,0);
  uStack_8._0_1_ = 0x37;
  piStack_14c = puVar8;
  puStack_148 = puVar8;
  if (puVar8 == (undefined4 *)0x0) {
    puVar8 = (undefined4 *)0x0;
  }
  else {
    FUN_6f055c90();
    *puVar8 = CSignalMode::vftable;
  }
  uStack_8._0_1_ = 0x1e;
  if (puVar8 != (undefined4 *)0x0) {
    puVar8[1] = puVar8[1] + 1;
  }
  puVar3 = (undefined4 *)param_1[0x89];
  if (puVar3 != (undefined4 *)0x0) {
    piVar7 = puVar3 + 1;
    *piVar7 = *piVar7 + -1;
    if (*piVar7 == 0) {
      (**(code **)*puVar3)();
    }
  }
  param_1[0x89] = puVar8;
  piStack_14c = (int *)Ordinal_401(0x10,&DAT_6f98c4f8,0x20a,0);
  uStack_8._0_1_ = 0x38;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    iVar5 = 0;
  }
  else {
    iVar5 = FUN_6f383b40(param_1);
  }
  uStack_8._0_1_ = 0x1e;
  if (iVar5 != 0) {
    *(int *)(iVar5 + 4) = *(int *)(iVar5 + 4) + 1;
  }
  puVar8 = (undefined4 *)param_1[0x90];
  if (puVar8 != (undefined4 *)0x0) {
    piVar7 = puVar8 + 1;
    *piVar7 = *piVar7 + -1;
    if (*piVar7 == 0) {
      (**(code **)*puVar8)();
    }
  }
  param_1[0x90] = iVar5;
  piStack_14c = (int *)Ordinal_401(0x10,&DAT_6f98c4f8,0x20b,0);
  uStack_8._0_1_ = 0x39;
  puStack_148 = piStack_14c;
  if (piStack_14c == (int *)0x0) {
    iVar5 = 0;
  }
  else {
    iVar5 = FUN_6f383e80();
  }
  uStack_8 = CONCAT31(uStack_8._1_3_,0x1e);
  if (iVar5 != 0) {
    *(int *)(iVar5 + 4) = *(int *)(iVar5 + 4) + 1;
  }
  puVar8 = (undefined4 *)param_1[0x91];
  if (puVar8 != (undefined4 *)0x0) {
    piVar7 = puVar8 + 1;
    *piVar7 = *piVar7 + -1;
    if (*piVar7 == 0) {
      (**(code **)*puVar8)();
    }
  }
  param_1[0x91] = iVar5;
  FUN_6f357810(param_1[0x95],1);
  (**(code **)(*(int *)param_1[0xef] + 8))(0x1a0066,0x1a0066,param_1[0x85]);
  (**(code **)(*(int *)param_1[0xef] + 8))(0x1a0067,0x1a0067,param_1[0x85]);
  FUN_6f356ac0(param_1[0x85],1);
  FUN_6f175d80();
  FUN_6f023e00();
  FUN_6f023ed0(0x2a,&uStack_154);
  param_1[0x74] = uStack_154;
  FUN_6f023ed0(0x3f,&uStack_154);
  param_1[0x75] = uStack_154;
  FUN_6f023ed0(0x2b,&uStack_154);
  param_1[0x76] = uStack_154;
  FUN_6f355fd0(8);
  FUN_6f33ce20();
  FUN_6f352d70(0);
  ExceptionList = pvStack_10;
  FUN_6f771125();
  return;
}


