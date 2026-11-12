

void __thiscall
FUN_6f393280(int param_1,float param_2,float param_3,undefined4 param_4,float param_5,
            undefined4 *param_6,int param_7)

{
  int iVar1;
  float fVar2;
  int iVar3;
  uint uVar4;
  undefined4 uVar5;
  float fVar6;
  float fVar7;
  
  iVar3 = FUN_6f34f3a0();
  if ((iVar3 != 0) && (iVar3 = FUN_6f350a90(), iVar3 != 0)) {
    *(int *)(param_1 + 0x5e0) = *(int *)(param_1 + 0x5e0) + 1;
    iVar3 = *(int *)(param_1 + 0x5d8);
    uVar4 = *(uint *)(param_1 + 0x5e0) & 0xf;
    if (*(int *)(iVar3 + uVar4 * 0x28) == 0) {
      *(uint *)(param_1 + 0x5e0) = *(uint *)(param_1 + 0x5e0) - 1;
      return;
    }
    iVar1 = iVar3 + uVar4 * 0x28;
    fVar6 = *(float *)(param_1 + 0x758);
    fVar2 = *(float *)(param_1 + 0x764);
    fVar7 = *(float *)(param_1 + 0x770);
    *(ulonglong *)(iVar1 + 8) =
         CONCAT44(*(float *)(param_1 + 0x754) * param_2 + *(float *)(param_1 + 0x760) * param_3 +
                  *(float *)(param_1 + 0x76c),
                  *(float *)(param_1 + 0x75c) * param_3 + *(float *)(param_1 + 0x750) * param_2 +
                  *(float *)(param_1 + 0x768));
    *(float *)(iVar1 + 0x10) = fVar6 * param_2 + fVar2 * param_3 + fVar7;
    fVar6 = *(float *)(iVar3 + 0xc + uVar4 * 0x28);
    fVar2 = *(float *)(iVar1 + 8);
    *(undefined4 *)(iVar3 + 0x10 + uVar4 * 0x28) = 0;
    fVar7 = *(float *)(param_1 + 0x644);
    if ((*(float *)(param_1 + 0x644) <= fVar6) &&
       (fVar7 = fVar6, *(float *)(param_1 + 0x64c) < fVar6)) {
      fVar7 = *(float *)(param_1 + 0x64c);
    }
    fVar6 = *(float *)(param_1 + 0x648);
    if ((*(float *)(param_1 + 0x648) <= fVar2) &&
       (fVar6 = fVar2, *(float *)(param_1 + 0x650) < fVar2)) {
      fVar6 = *(float *)(param_1 + 0x650);
    }
    *(float *)(iVar1 + 8) = fVar6;
    *(float *)(iVar3 + 0xc + uVar4 * 0x28) = fVar7;
    *(undefined4 *)(iVar3 + 0x20 + uVar4 * 0x28) = 1;
    *(undefined4 *)(iVar3 + 0x18 + uVar4 * 0x28) = 0;
    if (param_6 == (undefined4 *)0x0) {
      FUN_6f02a260(&DAT_6f98b894,0);
      uVar5 = 0;
    }
    else {
      uVar5 = *param_6;
    }
    *(undefined4 *)(iVar3 + 0x14 + uVar4 * 0x28) = uVar5;
    *(int *)(iVar3 + 0x1c + uVar4 * 0x28) = param_7;
    FUN_6f02a260(&DAT_6f98b8a0,0);
    if (*(undefined4 **)(iVar3 + 0x14 + uVar4 * 0x28) == param_6) {
      if (param_5 <= 0.0) {
        param_5 = DAT_6f95fe7c;
      }
      *(float *)(iVar3 + 4 + uVar4 * 0x28) = param_5;
      FUN_6f186590(1,0);
      FUN_6f186590(1,1);
    }
    else {
      if (param_5 <= 0.0) {
        param_5 = DAT_6f95d544;
      }
      *(float *)(iVar3 + 4 + uVar4 * 0x28) = param_5;
      if (param_7 == 0) {
        FUN_6f186590(1,0);
      }
      else {
        FUN_6f186590(2,0);
        FUN_6f186590(2,1);
        FUN_6f33bc20();
      }
    }
    FUN_6f18ec20(iVar3 + 8 + uVar4 * 0x28,0);
    FUN_6f18ed50(0);
    FUN_6f186fc0(*(undefined4 *)(iVar3 + 0x14 + uVar4 * 0x28));
  }
  return;
}



### SEED 0x6f1ee6c3
  (no xrefs-to)

