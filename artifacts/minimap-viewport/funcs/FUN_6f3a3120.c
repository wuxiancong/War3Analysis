

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void __fastcall FUN_6f3a3120(uint param_1)

{
  bool bVar1;
  bool bVar2;
  undefined1 auVar3 [12];
  undefined1 auVar4 [12];
  int iVar5;
  float *pfVar6;
  int iVar7;
  float fVar8;
  undefined8 uVar9;
  undefined1 auVar10 [16];
  uint uVar11;
  float fVar12;
  uint uVar13;
  float fVar14;
  float fVar15;
  undefined1 auVar16 [16];
  undefined1 auVar17 [16];
  undefined1 auVar18 [16];
  undefined1 auVar20 [16];
  undefined1 auVar21 [16];
  undefined1 auVar22 [16];
  float fVar23;
  float fVar24;
  float fVar25;
  undefined *puVar26;
  undefined4 uStack_1e0;
  undefined4 uStack_1dc;
  undefined4 uStack_1d8;
  undefined4 uStack_1d4;
  undefined4 uStack_1d0;
  undefined4 uStack_1cc;
  undefined4 uStack_1c8;
  undefined4 uStack_1c4;
  undefined4 uStack_1c0;
  undefined4 uStack_1bc;
  undefined4 uStack_1b8;
  undefined4 uStack_1b4;
  undefined4 uStack_1b0;
  undefined4 uStack_1ac;
  undefined4 uStack_1a8;
  undefined4 uStack_1a4;
  undefined4 uStack_1a0;
  undefined4 uStack_19c;
  undefined4 uStack_198;
  undefined4 uStack_194;
  undefined4 uStack_190;
  undefined4 uStack_18c;
  undefined4 uStack_188;
  undefined4 uStack_184;
  undefined4 uStack_180;
  undefined4 uStack_17c;
  undefined4 uStack_178;
  undefined4 uStack_174;
  undefined4 uStack_170;
  undefined4 uStack_16c;
  undefined4 uStack_168;
  undefined4 uStack_164;
  undefined4 uStack_160;
  undefined4 uStack_15c;
  undefined4 uStack_158;
  undefined4 uStack_154;
  float fStack_150;
  float fStack_14c;
  float fStack_148;
  float fStack_144;
  float fStack_140;
  float fStack_13c;
  float fStack_138;
  undefined4 uStack_134;
  undefined4 uStack_130;
  float fStack_12c;
  float fStack_128;
  float fStack_124;
  uint uStack_11c;
  float fStack_118;
  float fStack_114;
  float fStack_110;
  undefined8 uStack_10c;
  float fStack_104;
  byte bStack_f9;
  int *piStack_f8;
  int *piStack_f4;
  undefined4 uStack_f0;
  undefined4 uStack_ec;
  undefined4 uStack_e4;
  undefined4 uStack_dc;
  undefined4 uStack_d8;
  undefined4 uStack_d4;
  undefined4 uStack_d0;
  undefined4 uStack_cc;
  undefined4 uStack_c8;
  undefined4 uStack_c4;
  undefined4 uStack_c0;
  undefined4 uStack_bc;
  undefined4 uStack_b8;
  undefined4 uStack_b4;
  undefined4 uStack_b0;
  undefined4 uStack_ac;
  undefined4 uStack_a8;
  float fStack_a4;
  float afStack_a0 [11];
  undefined8 uStack_74;
  undefined4 uStack_6c;
  undefined8 uStack_68;
  undefined4 uStack_60;
  undefined8 uStack_5c;
  undefined4 uStack_54;
  undefined8 uStack_50;
  undefined4 uStack_48;
  undefined8 uStack_44;
  undefined4 uStack_3c;
  undefined8 uStack_38;
  undefined4 uStack_30;
  undefined8 uStack_2c;
  undefined4 uStack_24;
  undefined8 uStack_20;
  undefined4 uStack_18;
  uint uStack_14;
  undefined1 auVar19 [16];
  
  uStack_14 = DAT_6fb6a774 ^ (uint)&stack0xfffffff0;
  uStack_11c = param_1;
  FUN_6f0e44a0();
  uStack_180 = _DAT_6f95ac20;
  uStack_17c = _UNK_6f95ac24;
  uStack_178 = _UNK_6f95ac28;
  uStack_174 = _UNK_6f95ac2c;
  uStack_170 = _DAT_6f95ac20;
  uStack_16c = _UNK_6f95ac24;
  uStack_168 = _UNK_6f95ac28;
  uStack_164 = _UNK_6f95ac2c;
  uStack_160 = _DAT_6f95ac20;
  uStack_15c = _UNK_6f95ac24;
  uStack_158 = _UNK_6f95ac28;
  uStack_154 = _UNK_6f95ac2c;
  uStack_1b0 = _DAT_6f95ac20;
  uStack_1ac = _UNK_6f95ac24;
  uStack_1a8 = _UNK_6f95ac28;
  uStack_1a4 = _UNK_6f95ac2c;
  uStack_1a0 = _DAT_6f95ac20;
  uStack_19c = _UNK_6f95ac24;
  uStack_198 = _UNK_6f95ac28;
  uStack_194 = _UNK_6f95ac2c;
  uStack_190 = _DAT_6f95ac20;
  uStack_18c = _UNK_6f95ac24;
  uStack_188 = _UNK_6f95ac28;
  uStack_184 = _UNK_6f95ac2c;
  FUN_6f0d0af0();
  if ((((*(byte *)(param_1 + 0xb0) & 3) != 0) || (*(int *)(param_1 + 0x624) == 0)) ||
     (*(int *)(param_1 + 0x1cc) == 0)) goto code_r0x6f3a4001;
  fStack_150 = 0.0;
  fStack_14c = 0.0;
  fStack_148 = 0.0;
  fStack_144 = 0.0;
  (**(code **)(*(int *)(param_1 + 0xb4) + 0x10))(&fStack_150);
  pfVar6 = &fStack_140;
  FUN_6f34f3a0(pfVar6);
  FUN_6f34da20();
  FUN_6f3431c0(pfVar6);
  fStack_128 = *(float *)(param_1 + 0x75c) * fStack_13c + *(float *)(param_1 + 0x750) * fStack_140 +
               *(float *)(param_1 + 0x768);
  fStack_12c = *(float *)(param_1 + 0x754) * fStack_140 + *(float *)(param_1 + 0x760) * fStack_13c +
               *(float *)(param_1 + 0x76c);
  fStack_124 = *(float *)(param_1 + 0x758) * fStack_140 + *(float *)(param_1 + 0x764) * fStack_13c +
               *(float *)(param_1 + 0x770);
  FUN_6f0e3a00();
  FUN_6f0e3910();
  iVar5 = FUN_6f34f3a0();
  uStack_1e0 = 0;
  uStack_1dc = 0;
  uStack_1d8 = 0;
  uStack_1d4 = 0;
  (**(code **)(*(int *)(*(int *)(iVar5 + 0x3bc) + 0xb4) + 0x10))(&uStack_1e0);
  FUN_6f0a2780();
  FUN_6f0a3d80();
  FUN_6f0d0af0();
  FUN_6f0e3a00();
  FUN_6f0e3910();
  uStack_d8 = 0;
  uStack_d4 = 0;
  uStack_d0 = 0;
  uStack_cc = 0;
  uStack_c8 = 0;
  uStack_c4 = 0;
  uStack_c0 = 0;
  uStack_bc = 0;
  uStack_b8 = 0;
  uStack_b4 = 0;
  uStack_b0 = 0;
  uStack_ac = 0;
  uStack_a8 = 0;
  fStack_a4 = 0.0;
  afStack_a0[0] = 0.0;
  afStack_a0[1] = 0.0;
  afStack_a0[2] = 0.0;
  afStack_a0[3] = 0.0;
  afStack_a0[4] = 0.0;
  afStack_a0[5] = 0.0;
  afStack_a0[6] = 0.0;
  afStack_a0[7] = 0.0;
  afStack_a0[8] = 0.0;
  afStack_a0[9] = 0.0;
  FUN_6f0d2370(&uStack_d8);
  pfVar6 = afStack_a0;
  iVar5 = 4;
  do {
    iVar7 = iVar5;
    fVar14 = pfVar6[-0xc];
    iVar5 = iVar7 + -1;
    if ((fStack_138 < fVar14) && (*pfVar6 < fStack_138)) {
      fVar12 = fVar14 - *pfVar6;
      if (DAT_6f95be1c <= (float)(double)((ulonglong)(double)fVar12 & DAT_6f95a890)) {
        fVar8 = (fVar14 - fStack_138) / fVar12;
        fStack_104 = fVar14 + fVar8 * fVar12;
        *(ulonglong *)(pfVar6 + -2) =
             CONCAT44(pfVar6[-0xd] + (pfVar6[-0xd] - pfVar6[-1]) * fVar8,
                      pfVar6[-0xe] + (pfVar6[-0xe] - pfVar6[-2]) * fVar8);
        *pfVar6 = fStack_104;
      }
    }
    pfVar6 = pfVar6 + 3;
  } while (iVar5 != 0);
  pfVar6 = &fStack_a4;
  iVar7 = iVar7 + 3;
  fStack_118 = DAT_6f98e014;
  piStack_f8 = (int *)DAT_6f951e30;
  fStack_114 = DAT_6f98e014;
  piStack_f4 = (int *)DAT_6f951e30;
  do {
    fVar14 = pfVar6[-1];
    if (fVar14 <= (float)piStack_f8) {
      piStack_f8 = (int *)fVar14;
    }
    if (fStack_118 <= fVar14) {
      fStack_118 = fVar14;
    }
    fVar14 = *pfVar6;
    if (fVar14 <= (float)piStack_f4) {
      piStack_f4 = (int *)fVar14;
    }
    if (fStack_114 <= fVar14) {
      fStack_114 = fVar14;
    }
    pfVar6 = pfVar6 + 3;
    iVar7 = iVar7 + -1;
  } while (iVar7 != 0);
  FUN_6f0e3940();
  FUN_6f0e3970();
  fVar12 = ((*(float *)(param_1 + 0x75c) * fStack_114 + *(float *)(param_1 + 0x750) * fStack_118 +
            *(float *)(param_1 + 0x768)) -
           (*(float *)(param_1 + 0x75c) * (float)piStack_f4 +
            *(float *)(param_1 + 0x750) * (float)piStack_f8 + *(float *)(param_1 + 0x768))) *
           DAT_6f950d88;
  uVar11 = (uint)fVar12 ^ DAT_6f95a590;
  fVar14 = ((*(float *)(param_1 + 0x760) * fStack_114 + *(float *)(param_1 + 0x754) * fStack_118 +
            *(float *)(param_1 + 0x76c)) -
           (*(float *)(param_1 + 0x760) * (float)piStack_f4 +
            *(float *)(param_1 + 0x754) * (float)piStack_f8 + *(float *)(param_1 + 0x76c))) *
           DAT_6f950d88;
  uVar13 = (uint)fVar14 ^ DAT_6f95a590;
  *(ulonglong *)(param_1 + 0x584) = CONCAT44(fVar14,uVar11);
  *(undefined4 *)(param_1 + 0x58c) = 0;
  *(ulonglong *)(param_1 + 0x590) = CONCAT44(uVar13,uVar11);
  *(undefined4 *)(param_1 + 0x598) = 0;
  *(ulonglong *)(param_1 + 0x59c) = CONCAT44(fVar14,fVar12);
  *(undefined4 *)(param_1 + 0x5a4) = 0;
  fStack_104 = 0.0;
  *(ulonglong *)(param_1 + 0x5a8) = CONCAT44(uVar13,fVar12);
  *(undefined4 *)(param_1 + 0x5b0) = 0;
  FUN_6f0e38e0();
  FUN_6f0e38d0();
  uStack_f0 = 0xe;
  uStack_ec = 1;
  uStack_e4 = FUN_6f197840();
  uStack_dc = 2;
  FUN_6f0e35b0(0xc,0x6fb69b70,0,0,0,0,0,0x6fb69b7c,8,0,0);
  bStack_f9 = *(byte *)(param_1 + 0xac);
  uStack_130 = 0;
  uStack_134 = 0;
  func_0x6f0e36b0();
  func_0x6f0e36b0();
  FUN_6f0e3710((uint)bStack_f9 << 0x18);
  FUN_6f0e3710(0xffffffff);
  FUN_6f0e34b0();
  FUN_6f0e3520(&UNK_6f98e274);
  FUN_6f0e3670();
  if (*(int *)(param_1 + 0x630) != 0) {
    FUN_6f0cb480();
    thunk_FUN_6f139800();
  }
  FUN_6f0e35b0(0xc,0x6fb69b70,0,0,0,0,0,0x6fb69b7c,8,0,0);
  FUN_6f0e3550(&UNK_6f98e274);
  uStack_e4 = FUN_6f197840();
  fVar14 = *(float *)(param_1 + 0x404);
  if (fRam6fb69bac < fVar14) {
    fVar14 = DAT_6f95ad98 - fVar14;
  }
  FUN_6f0e3710((int)((fVar14 / fRam6fb69bac) * DAT_6f9641c0 + DAT_6f95d80c) << 0x18);
  fVar14 = 0.0;
  piStack_f8 = (int *)(param_1 + 0x2fc);
  fStack_118 = 0.0;
  fStack_114 = 0.0;
  piStack_f4 = piStack_f8;
  do {
    fVar12 = fStack_114;
    if (*(int *)((int)fStack_114 + *(int *)(param_1 + 0x2e4)) != 0) {
      FUN_6f0e3710(*(undefined4 *)(param_1 + 0x23c + (int)fStack_114));
      FUN_6f0e34b0();
      iVar5 = *(int *)((int)fVar12 + *(int *)(param_1 + 0x2e4));
      fVar14 = fStack_118;
      if (iVar5 != 0) {
        iVar7 = iVar5 * 0xc;
        do {
          iVar7 = iVar7 + -0xc;
          iVar5 = iVar5 + -1;
          uStack_10c = *(undefined8 *)(*piStack_f8 + iVar7);
          fStack_104 = *(float *)(*piStack_f8 + 8 + iVar7);
          if ((DAT_6fbe6584 == 0) || (fStack_104 == _DAT_6f950d84)) {
            fStack_104 = 0.0;
            uStack_180 = uStack_1b0;
            uStack_17c = uStack_1ac;
            uStack_178 = uStack_1a8;
            uStack_174 = uStack_1a4;
            uStack_170 = uStack_1a0;
            uStack_16c = uStack_19c;
            uStack_168 = uStack_198;
            uStack_164 = uStack_194;
            uStack_160 = uStack_190;
            uStack_15c = uStack_18c;
            uStack_158 = uStack_188;
            uStack_154 = uStack_184;
            FUN_6f1ab2d0(&uStack_10c);
            FUN_6f0e3970();
            FUN_6f0e3540();
          }
          else {
            fStack_118 = 1.4013e-45;
          }
          fVar14 = fStack_118;
          param_1 = uStack_11c;
        } while (iVar5 != 0);
      }
    }
    piStack_f8 = piStack_f8 + 4;
    fStack_114 = (float)((int)fStack_114 + 4);
  } while ((uint)fStack_114 < 0x40);
  if (fVar14 != 0.0) {
    FUN_6f0e3710(*(undefined4 *)(param_1 + 0x7c4));
    FUN_6f0e34b0();
    piStack_f8 = (int *)0x0;
    do {
      iVar5 = *(int *)((int)piStack_f8 + *(int *)(param_1 + 0x2e4));
      if (iVar5 != 0) {
        iVar7 = iVar5 * 0xc;
        do {
          iVar7 = iVar7 + -0xc;
          iVar5 = iVar5 + -1;
          uStack_10c = *(undefined8 *)(*piStack_f4 + iVar7);
          fStack_104 = *(float *)(*piStack_f4 + 8 + iVar7);
          if (fStack_104 != 0.0) {
            fStack_104 = 0.0;
            uStack_180 = uStack_1b0;
            uStack_17c = uStack_1ac;
            uStack_178 = uStack_1a8;
            uStack_174 = uStack_1a4;
            uStack_170 = uStack_1a0;
            uStack_16c = uStack_19c;
            uStack_168 = uStack_198;
            uStack_164 = uStack_194;
            uStack_160 = uStack_190;
            uStack_15c = uStack_18c;
            uStack_158 = uStack_188;
            uStack_154 = uStack_184;
            FUN_6f1ab2d0(&uStack_10c);
            FUN_6f0e3970();
            FUN_6f0e3540();
          }
          param_1 = uStack_11c;
        } while (iVar5 != 0);
      }
      piStack_f4 = piStack_f4 + 4;
      piStack_f8 = piStack_f8 + 1;
    } while (piStack_f8 < (int *)0x40);
  }
  FUN_6f0e3640();
  FUN_6f0e3670();
  if (DAT_6f95ad98 <= *(float *)(param_1 + 0x404)) {
    *(undefined4 *)(param_1 + 0x404) = 0;
  }
  uStack_e4 = FUN_6f197840();
  uStack_dc = 0;
  FUN_6f0e3710((uint)*(byte *)(param_1 + 0xac) << 0x18 | 0xffffff);
  FUN_6f0e34b0();
  FUN_6f0e3970();
  fVar25 = fStack_128 + *(float *)(param_1 + 0x584);
  fVar14 = *(float *)(param_1 + 0x588) + fStack_12c;
  fVar24 = fStack_128 + *(float *)(param_1 + 0x590);
  fVar8 = *(float *)(param_1 + 0x594) + fStack_12c;
  fVar15 = *(float *)(param_1 + 0x59c) + fStack_128;
  fVar12 = *(float *)(param_1 + 0x5a0) + fStack_12c;
  fStack_128 = fStack_128 + *(float *)(param_1 + 0x5a8);
  fVar23 = fStack_144 - fStack_14c;
  auVar10._0_4_ = fStack_148 - fStack_150;
  uStack_11c = (uint)(fVar25 <= 0.0);
  uStack_10c = 0;
  fStack_104 = 0.0;
  bVar1 = fVar8 <= 0.0;
  bVar2 = auVar10._0_4_ <= fVar12;
  uStack_1d0 = 0;
  uStack_1cc = 0;
  uStack_1c8 = 0;
  uStack_1c4 = 0;
  uStack_1c0 = 0;
  uStack_1bc = 0;
  uStack_1b8 = 0;
  uStack_1b4 = 0;
  auVar16._4_4_ = fVar15;
  auVar16._0_4_ = fVar25;
  auVar16._8_4_ = fVar15;
  auVar16._12_4_ = fStack_128;
  auVar21._8_8_ = auVar16._8_8_;
  auVar21._4_4_ = fVar24;
  auVar21._0_4_ = fVar25;
  auVar17 = maxps(auVar21,ZEXT816(0));
  auVar18._0_8_ = auVar17._0_8_;
  auVar3._4_4_ = auVar17._8_4_;
  auVar3._0_4_ = auVar17._8_4_;
  auVar3._8_4_ = auVar17._12_4_;
  auVar18._8_8_ = auVar3._4_8_;
  auVar17._4_4_ = fVar23;
  auVar17._0_4_ = fVar23;
  auVar17._8_4_ = fVar23;
  auVar17._12_4_ = fVar23;
  auVar17 = minps(auVar18,auVar17);
  auVar20._4_4_ = fVar12;
  auVar20._0_4_ = fVar14;
  auVar20._8_4_ = fVar12;
  auVar20._12_4_ = *(float *)(param_1 + 0x5ac) + fStack_12c;
  auVar19._8_8_ = auVar20._8_8_;
  auVar19._4_4_ = fVar8;
  auVar19._0_4_ = fVar14;
  auVar21 = maxps(auVar19,ZEXT816(0));
  uStack_3c = 0;
  auVar22._0_8_ = auVar21._0_8_;
  auVar10._4_4_ = auVar10._0_4_;
  auVar10._8_4_ = auVar10._0_4_;
  auVar10._12_4_ = auVar10._0_4_;
  auVar4._4_4_ = auVar21._8_4_;
  auVar4._0_4_ = auVar21._8_4_;
  auVar4._8_4_ = auVar21._12_4_;
  auVar22._8_8_ = auVar4._4_8_;
  auVar21 = minps(auVar22,auVar10);
  uStack_44 = CONCAT44(auVar21._0_4_,auVar17._0_4_);
  uStack_38 = CONCAT44(auVar21._4_4_,auVar17._4_4_);
  uStack_30 = 0;
  uStack_2c = CONCAT44(auVar21._8_4_,auVar17._8_4_);
  uStack_24 = 0;
  uStack_20 = CONCAT44(auVar21._12_4_,auVar17._12_4_);
  uStack_18 = 0;
  fStack_110 = auVar10._0_4_;
  if ((((uStack_11c != 0) || (fVar23 <= fVar15)) || (bVar1)) || (bVar2)) {
    uStack_74 = 0;
    uStack_68 = 0;
    uStack_5c = 0;
    uStack_50 = 0;
    if (fVar23 <= fVar15) {
      if (bVar2) {
        uStack_74 = uStack_44;
        uStack_68 = uStack_38;
        uStack_5c = uStack_20;
      }
      else {
        if (!bVar1) {
          uStack_74 = uStack_2c;
          uStack_5c = uStack_38;
code_r0x6f3a3f50:
          uStack_68 = uStack_44;
          uVar9 = uStack_20;
          goto code_r0x6f3a3f60;
        }
        uStack_74 = uStack_38;
        uStack_68 = uStack_44;
        uStack_5c = uStack_2c;
      }
    }
    else if (uStack_11c == 0) {
      if (bVar2) {
        uStack_74 = uStack_44;
        uStack_68 = uStack_38;
        uStack_5c = uStack_20;
        uVar9 = uStack_2c;
code_r0x6f3a3f60:
        uStack_50 = uVar9;
      }
      else if (bVar1) {
        uStack_74 = uStack_38;
        uStack_5c = uStack_2c;
        goto code_r0x6f3a3f50;
      }
    }
    else if (bVar2) {
      uStack_74 = uStack_2c;
      uStack_68 = uStack_20;
      uStack_5c = uStack_38;
    }
    else {
      uStack_74 = uStack_44;
      uStack_68 = uStack_2c;
      uStack_5c = uStack_20;
      uVar9 = uStack_38;
      if (!bVar1) goto code_r0x6f3a3f60;
    }
    uStack_48 = 0;
    uStack_54 = 0;
    uStack_60 = 0;
    uStack_6c = 0;
    FUN_6f0e35b0(0xc,0x6fb69b70,0,0,0,0,0,0x6fbe6e2c,8,0,0);
    puVar26 = &UNK_6f98e2ec;
  }
  else {
    FUN_6f0e35b0(0xc,0x6fb69b70,0,0,0,0,0,0x6fbe6e2c,8,0,0);
    puVar26 = &UNK_6f98e27c;
  }
  FUN_6f0e3550(puVar26);
  FUN_6f0e3540();
  FUN_6f0e3640();
  FUN_6f0e3670();
  if ((*(int *)(param_1 + 0x628) != 0) && (*(int *)(param_1 + 0x5b4) != 0)) {
    FUN_6f0cb480();
    thunk_FUN_6f139800();
  }
  FUN_6f0e3710(uStack_130);
  FUN_6f0e3710(uStack_134);
code_r0x6f3a4001:
  FUN_6f771125();
  return;
}


