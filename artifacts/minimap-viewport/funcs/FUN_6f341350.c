

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void __thiscall FUN_6f341350(int param_1,undefined4 param_2,undefined4 param_3)

{
  uint uVar1;
  uint uVar2;
  float10 fVar3;
  float fVar4;
  float fStack_70;
  float fStack_6c;
  float afStack_68 [4];
  undefined4 uStack_58;
  undefined4 uStack_54;
  undefined4 uStack_50;
  undefined4 uStack_4c;
  undefined4 uStack_48;
  undefined4 uStack_44;
  undefined4 uStack_40;
  undefined4 uStack_3c;
  undefined4 uStack_38;
  undefined4 uStack_34;
  undefined4 uStack_30;
  undefined4 uStack_2c;
  undefined4 uStack_28;
  undefined4 uStack_24;
  float afStack_20 [4];
  undefined4 uStack_10;
  undefined4 uStack_c;
  uint uStack_8;
  
  uStack_8 = DAT_6fb6a774 ^ (uint)&stack0xfffffffc;
  FUN_6f346a60(param_3);
  uVar2 = *(uint *)(param_1 + 0x20);
  uStack_10 = 0x449f6000;
  afStack_20[0] = _DAT_6f9714d0;
  afStack_20[1] = (float)_UNK_6f9714d4;
  afStack_20[2] = (float)_UNK_6f9714d8;
  afStack_20[3] = (float)_UNK_6f9714dc;
  uStack_c = 0x44960000;
  afStack_68[0] = _DAT_6f9714a0;
  afStack_68[1] = (float)_UNK_6f9714a4;
  afStack_68[2] = (float)_UNK_6f9714a8;
  afStack_68[3] = (float)_UNK_6f9714ac;
  uStack_28 = 0x43200000;
  uStack_58 = _DAT_6f971490;
  uStack_54 = _UNK_6f971494;
  uStack_50 = _UNK_6f971498;
  uStack_4c = _UNK_6f97149c;
  uStack_24 = 0x43200000;
  uVar1 = uVar2 + *(int *)(param_1 + 0x24) * 6;
  uStack_10 = 0x43a60000;
  uStack_c = 0x43a78000;
  uStack_48 = _DAT_6f971480;
  uStack_44 = _UNK_6f971484;
  uStack_40 = _UNK_6f971488;
  uStack_3c = _UNK_6f97148c;
  uStack_38 = _DAT_6f9714b0;
  uStack_34 = _UNK_6f9714b4;
  uStack_30 = _UNK_6f9714b8;
  uStack_2c = _UNK_6f9714bc;
  fVar4 = (afStack_68[-(uint)(uVar1 < 0x12) & uVar1] * _DAT_6f95a588) / _DAT_6f95a58c;
  afStack_20[0] = _DAT_6f9714c0;
  afStack_20[1] = (float)_UNK_6f9714c4;
  afStack_20[2] = (float)_UNK_6f9714c8;
  afStack_20[3] = (float)_UNK_6f9714cc;
  FUN_6f345760(0,afStack_20[-(uint)(uVar2 < 6) & uVar2],param_2,0);
  FUN_6f345760(1,0x459c4000,param_2,0);
  FUN_6f345760(2,(afStack_20[-(uint)(uVar2 < 6) & uVar2] * _DAT_6f95a588) / _DAT_6f95a58c,param_2,0)
  ;
  FUN_6f345760(3,0x3f9c61ab,param_2,0);
  FUN_6f345760(4,0,param_2,0);
  FUN_6f345760(5,fVar4,param_2,0);
  FUN_6f345760(6,0,param_2,0);
  fVar3 = (float10)FUN_6f02a2f0(*(undefined4 *)(param_1 + 0x20));
  fStack_70 = (float)fVar3;
  if (fStack_70 == _DAT_6f950d84) {
    fVar3 = (float10)FUN_6f02a2f0(0);
    fStack_70 = (float)fVar3;
  }
  fVar3 = (float10)FUN_6f02a2f0(*(undefined4 *)(param_1 + 0x20));
  fStack_6c = (float)fVar3;
  if (fStack_6c == _DAT_6f950d84) {
    fVar3 = (float10)FUN_6f02a2f0(0);
    fStack_6c = (float)fVar3;
  }
  FUN_6f345760(8,fStack_70,param_2,0);
  FUN_6f345760(9,fStack_6c,param_2,1);
  FUN_6f771125();
  return;
}


