

undefined4 __thiscall FUN_6f3a45a0(int *param_1,float param_2,undefined4 param_3,undefined4 param_4)

{
  float fVar1;
  uint uVar2;
  int iVar3;
  undefined4 uVar4;
  int iVar5;
  int *piVar6;
  float10 fVar7;
  float fVar8;
  undefined4 uVar9;
  void *pvStack_10;
  undefined *puStack_c;
  undefined4 uStack_8;
  
  fVar1 = DAT_6f95ad98;
  uStack_8 = 0xffffffff;
  puStack_c = &DAT_6f8e0860;
  pvStack_10 = ExceptionList;
  uVar2 = DAT_6fb6a774 ^ (uint)&stack0xfffffffc;
  ExceptionList = &pvStack_10;
  fVar8 = param_2 + (float)param_1[0x101];
  param_1[0x101] = (int)fVar8;
  if (fVar1 <= fVar8) {
    fVar8 = fVar1;
  }
  param_1[0x101] = (int)fVar8;
  if ((*(byte *)(param_1 + 0x2c) & 3) == 0) {
    iVar3 = FUN_6f0a2300(param_2,param_3,param_4);
    if (iVar3 == 0) {
      ExceptionList = pvStack_10;
      return 0;
    }
    if ((param_1[0x73] == 0) && (iVar3 = (**(code **)(*param_1 + 0xe4))(uVar2), iVar3 == 0)) {
      FUN_6f3913b0();
    }
    else {
      FUN_6f0a2780();
      thunk_FUN_6f0cab90();
      thunk_FUN_6f0cab90();
      if (param_1[0x189] != 0) {
        param_1[0x18a] = 0;
        uVar4 = FUN_6f0a1970();
        uVar2 = 0;
        do {
          piVar6 = (int *)(param_1[0x176] + uVar2);
          if ((*piVar6 != 0) && (piVar6[8] != 0)) {
            iVar3 = FUN_6f0caa90(*piVar6,param_2,uVar4,0);
            if (iVar3 != 0) {
              param_1[0x18a] = 1;
            }
            fVar1 = (float)piVar6[1];
            piVar6[1] = (int)(fVar1 - param_2);
            if (fVar1 - param_2 < 0.0) {
              if (piVar6[6] == 0) {
                piVar6[6] = 1;
                if (piVar6[7] == 0) {
                  uVar9 = 1;
                }
                else {
                  uVar9 = 2;
                }
                fVar7 = (float10)FUN_6f186590(uVar9,0);
                piVar6[1] = (int)(float)fVar7;
              }
              else {
                piVar6[8] = 0;
                piVar6[7] = 0;
              }
            }
          }
          uVar2 = uVar2 + 0x28;
        } while (uVar2 < 0x280);
        uVar2 = 0;
        do {
          iVar3 = param_1[0x17b];
          if ((((*(int *)(iVar3 + uVar2) != 0) && (*(int *)(iVar3 + 0x20 + uVar2) != 0)) &&
              (*(int *)(iVar3 + 0x24 + uVar2) != 0)) &&
             (iVar3 = FUN_6f0caa90(*(int *)(iVar3 + uVar2),param_2,uVar4,0), iVar3 != 0)) {
            param_1[0x18a] = 1;
          }
          iVar3 = DAT_6fbe4238;
          uVar2 = uVar2 + 0x28;
        } while (uVar2 < 0x2800);
        iVar5 = FUN_6f30e9a0();
        if ((iVar5 == 0) || ((*(byte *)(*(int *)(iVar3 + 0x34) + 0x24) & 1) == 0)) {
          FUN_6f3b89f0(param_2,uVar4);
        }
        if (param_1[0x187] != 0) {
          FUN_6f0e38a0(0,0,0);
        }
      }
    }
  }
  ExceptionList = pvStack_10;
  return 1;
}



### SEED 0x6f3a3120
  (no xrefs-to)
NO FUNCTION; insns:
  6f3a3120  ??

### SEED 0x6f3a2e10
  (no xrefs-to)

