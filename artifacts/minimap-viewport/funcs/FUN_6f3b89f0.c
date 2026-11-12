

void __thiscall FUN_6f3b89f0(int param_1,float param_2,undefined4 param_3)

{
  undefined4 uVar1;
  undefined4 uVar2;
  byte bVar3;
  int iVar4;
  uint uVar5;
  undefined4 uVar6;
  undefined4 *puVar7;
  undefined4 uVar8;
  int iVar9;
  float fVar10;
  undefined8 uVar11;
  undefined4 uVar12;
  int iStack_80;
  int iStack_7c;
  int iStack_78;
  int iStack_74;
  uint uStack_70;
  int iStack_6c;
  uint uStack_68;
  uint uStack_64;
  undefined4 uStack_60;
  int iStack_5c;
  undefined4 uStack_58;
  int iStack_54;
  float fStack_50;
  float fStack_4c;
  int iStack_48;
  float fStack_44;
  float fStack_40;
  undefined4 uStack_3c;
  uint uStack_38;
  uint uStack_34;
  ushort auStack_30 [2];
  float fStack_2c;
  uint uStack_28;
  uint uStack_24;
  uint uStack_20;
  uint uStack_1c;
  uint uStack_18;
  uint uStack_14;
  int iStack_10;
  int iStack_c;
  int iStack_8;
  
  if ((*(int *)(param_1 + 0x624) != 0) &&
     (iStack_5c = DAT_6fbe4238, *(int *)(DAT_6fbe4238 + 0x3c0) != 0)) {
    iStack_10 = param_1;
    iVar4 = FUN_6f1c3330(*(undefined2 *)(DAT_6fbe4238 + 0x28));
    uStack_1c = (uint)*(byte *)(iVar4 + 0x30);
    iStack_48 = *(int *)(param_1 + 0x228);
    iStack_54 = *(int *)(param_1 + 0x22c);
    iStack_78 = *(int *)(param_1 + 0x224);
    iStack_6c = *(int *)(param_1 + 0x230);
    iStack_74 = FUN_6f630f60();
    uStack_58 = *(undefined4 *)(param_1 + 0x800);
    fStack_2c = *(float *)(param_1 + 0x810);
    uVar1 = *(undefined4 *)(param_1 + 0x804);
    uStack_38 = *(uint *)(iStack_74 + 4);
    uVar2 = *(undefined4 *)(param_1 + 0x80c);
    uStack_64 = *(uint *)(param_1 + 0x7f8);
    uStack_70 = *(uint *)(param_1 + 0x7fc);
    uStack_60 = *(undefined4 *)(param_1 + 0x808);
    fVar10 = 0.0;
    if ((fStack_2c < 0.0) || (fVar10 = DAT_6f95ad98, DAT_6f95ad98 < fStack_2c)) {
      fStack_2c = fVar10;
    }
    uStack_14 = 0;
    uStack_28 = 0;
    uStack_34 = 0;
    if (uStack_38 != 0) {
      bVar3 = (byte)uStack_1c & 0x1f;
      uStack_18 = 1 << bVar3 | 1U >> 0x20 - bVar3;
      do {
        if (uStack_38 <= uStack_14) break;
        iStack_8 = *(int *)(*(int *)(iStack_74 + 8) + uStack_34 * 4);
        if ((iStack_8 != 0) && (iVar4 = FUN_6f037350(), iVar4 != 0)) {
          iVar9 = 0;
          if (*(int *)(iVar4 + 0xc) == 0x2b61676c) {
            iVar9 = iVar4;
          }
          if ((iVar9 != 0) && (*(int *)(iVar9 + 0x20) == 0)) {
            fStack_50 = *(float *)(iStack_8 + 0x28);
            fStack_4c = *(float *)(iStack_8 + 0x2c);
            uStack_3c = *(undefined4 *)(iStack_8 + 0x30);
            fStack_44 = fStack_50;
            fStack_40 = fStack_4c;
            FUN_6f0528b0(DAT_6fbb82bc + 0x70);
            uStack_24 = ~((int)(uStack_24 + 0xfd000000 ^ uStack_24) >> 0x1f) &
                        uStack_24 + 0xfd800000;
            FUN_6f0528b0(DAT_6fbb82bc + 0x6c);
            uStack_20 = ~((int)(uStack_20 + 0xfd000000 ^ uStack_20) >> 0x1f) &
                        uStack_20 + 0xfd800000;
            iStack_c = FUN_6f052f30();
            iStack_c = iStack_c >> 2;
            iStack_80 = FUN_6f052f30();
            iStack_80 = iStack_80 >> 2;
            iStack_7c = iStack_c;
            if ((iStack_48 <= iStack_80) &&
               (((iStack_80 <= iStack_78 && (iStack_54 <= iStack_c)) && (iStack_c <= iStack_6c)))) {
              FUN_6f1bff40(&iStack_80,&uStack_1c,auStack_30,0xffff);
              FUN_6f632060(uStack_1c);
              if ((*(int *)(param_1 + 0x630) != 0) &&
                 ((((uStack_18 & auStack_30[0]) != 0 || ((uStack_18 & uStack_1c & 0xffff) == 0)) &&
                  (uVar5 = FUN_6f6311e0(), (uStack_18 & uVar5 & 0xffff) == 0)))) {
                uVar5 = FUN_6f631490();
                uStack_68 = (uint)(uStack_70 <= uVar5);
                if ((uStack_68 == 0) && (uStack_64 <= uVar5)) {
                  iStack_8 = 1;
LAB_6f3b8c85:
                  if (uStack_14 < *(uint *)(param_1 + 0x1a0)) {
                    uVar6 = *(undefined4 *)(*(int *)(param_1 + 0x1a4) + uStack_14 * 4);
                  }
                  else {
                    uVar6 = FUN_6f1850d0();
                    puVar7 = (undefined4 *)FUN_6f0a34b0();
                    uVar12 = 0;
                    uVar11 = 0;
                    *puVar7 = uVar6;
                    uVar8 = FUN_6f33e580(0,0,0);
                    FUN_6f324ad0(uVar8);
                    FUN_6f186a90(uVar8,uVar11,uVar12);
                    iStack_c = 0;
                    FUN_6f186590();
                  }
                  uStack_14 = uStack_14 + 1;
                }
                else {
                  iStack_8 = 0;
                  if (uStack_68 == 0) goto LAB_6f3b8c85;
                  if (uStack_28 < *(uint *)(param_1 + 0x1b0)) {
                    uVar6 = *(undefined4 *)(*(int *)(param_1 + 0x1b4) + uStack_28 * 4);
                    uStack_28 = uStack_28 + 1;
                  }
                  else {
                    uVar6 = FUN_6f1850d0();
                    puVar7 = (undefined4 *)FUN_6f0a34b0();
                    uVar12 = 0;
                    uVar11 = 0;
                    *puVar7 = uVar6;
                    uVar8 = FUN_6f33e580(0,0,0);
                    FUN_6f324ad0(uVar8);
                    FUN_6f186a90(uVar8,uVar11,uVar12);
                    iStack_c = 0;
                    FUN_6f186590();
                    uStack_28 = uStack_28 + 1;
                  }
                }
                FUN_6f186f10(CONCAT44(*(float *)(iStack_10 + 0x760) * fStack_4c +
                                      *(float *)(iStack_10 + 0x754) * fStack_50 +
                                      *(float *)(iStack_10 + 0x76c),
                                      *(float *)(iStack_10 + 0x75c) * fStack_4c +
                                      fStack_50 * *(float *)(iStack_10 + 0x750) +
                                      *(float *)(iStack_10 + 0x768)),
                             *(float *)(iStack_10 + 0x764) * fStack_4c +
                             *(float *)(iStack_10 + 0x758) * fStack_50 +
                             *(float *)(iStack_10 + 0x770));
                if (iStack_8 == 0) {
                  FUN_6f186f20(0x3f800000);
                  uVar8 = uVar1;
                  if (uStack_68 != 0) {
                    uVar8 = uVar2;
                  }
                }
                else {
                  FUN_6f186f20(uStack_58);
                  uVar8 = uStack_60;
                }
                FUN_6f186fc0(uVar8);
                param_1 = iStack_10;
                FUN_6f0caa90(uVar6,fStack_2c * param_2,param_3,0);
              }
            }
          }
        }
        uStack_34 = uStack_34 + 1;
      } while (uStack_34 < uStack_38);
    }
    *(undefined4 *)(param_1 + 0x1bc) = 1;
  }
  return;
}


