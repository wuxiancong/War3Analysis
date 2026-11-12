

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_6f345760(float param_1,float param_2,float param_3,float param_4)

{
  float fVar1;
  float *pfVar2;
  bool bVar3;
  float10 fVar4;
  float fVar5;
  float fStack_48;
  undefined4 uStack_44;
  float fStack_40;
  float fStack_3c;
  undefined4 uStack_38;
  float fStack_34;
  float fStack_30;
  undefined4 uStack_2c;
  float fStack_28;
  float fStack_24;
  undefined4 uStack_20;
  float fStack_1c;
  float fStack_18;
  float fStack_14;
  float fStack_10;
  float fStack_c;
  float fStack_8;
  
  fVar1 = param_1;
  fVar5 = 0.0;
  if ((float)(double)((ulonglong)(double)(param_3 - 0.0) & DAT_6f95a890) < DAT_6f956678) {
    FUN_6f346ae0(param_1);
    switch(fVar1) {
    case 0.0:
      param_1 = param_2;
      FUN_6f03afb0(&param_1);
      return;
    case 1.4013e-45:
      param_3 = param_2;
      FUN_6f03afb0(&param_3);
      return;
    case 2.8026e-45:
      fStack_10 = param_2;
      if (param_4 != 0.0) {
        fStack_10 = (param_2 * _DAT_6f95a588) / _DAT_6f95a58c;
      }
      break;
    case 4.2039e-45:
      fStack_14 = param_2;
      if (param_4 != 0.0) {
        fStack_14 = (param_2 * _DAT_6f95a588) / _DAT_6f95a58c;
      }
      FUN_6f045720(&fStack_14);
      return;
    case 5.60519e-45:
      fStack_18 = param_2;
      if (param_4 != 0.0) {
        fStack_18 = (param_2 * _DAT_6f95a588) / _DAT_6f95a58c;
      }
      FUN_6f045720(&fStack_18);
      return;
    case 7.00649e-45:
      fStack_1c = param_2;
      if (param_4 != 0.0) {
        fStack_1c = (param_2 * _DAT_6f95a588) / _DAT_6f95a58c;
      }
      FUN_6f045720(&fStack_1c);
      return;
    case 8.40779e-45:
      fStack_c = param_2;
      FUN_6f03afb0(&fStack_c);
      return;
    case 9.80909e-45:
      fStack_8 = param_2;
      FUN_6f03afb0(&fStack_8);
      return;
    case 1.12104e-44:
      FUN_6f03afb0(&param_2);
      return;
    case 1.26117e-44:
      bVar3 = param_4 != 0.0;
      param_4 = param_2;
      if (bVar3) {
        param_4 = (param_2 * _DAT_6f95a588) / _DAT_6f95a58c;
      }
      FUN_6f045720(&param_4);
      return;
    default:
      return;
    }
    FUN_6f045720(&fStack_10);
    return;
  }
  switch(param_1) {
  case 0.0:
    FUN_6f03adf0(&fStack_14);
    fVar5 = param_2 - fStack_14;
    break;
  case 1.4013e-45:
    FUN_6f03adf0(&fStack_10);
    fVar5 = param_2 - fStack_10;
    break;
  case 2.8026e-45:
    FUN_6f045740(&uStack_20);
    fVar4 = (float10)FUN_6f3426a0(uStack_20);
    param_1 = (float)fVar4;
    fVar5 = param_2;
    if (param_4 != 0.0) {
      fVar5 = (param_2 * _DAT_6f95a588) / _DAT_6f95a58c;
    }
    fVar4 = (float10)FUN_6f3426a0(fVar5);
    pfVar2 = &fStack_24;
    fStack_24 = (float)fVar4;
    fStack_28 = param_1;
    goto LAB_6f345bf0;
  case 4.2039e-45:
    FUN_6f045740(&uStack_2c);
    fVar4 = (float10)FUN_6f3426a0(uStack_2c);
    param_1 = (float)fVar4;
    fVar5 = param_2;
    if (param_4 != 0.0) {
      fVar5 = (param_2 * _DAT_6f95a588) / _DAT_6f95a58c;
    }
    fVar4 = (float10)FUN_6f3426a0(fVar5);
    pfVar2 = &fStack_30;
    fStack_30 = (float)fVar4;
    fStack_34 = param_1;
    goto LAB_6f345bf0;
  case 5.60519e-45:
    FUN_6f045740(&uStack_38);
    fVar4 = (float10)FUN_6f3426a0(uStack_38);
    param_1 = (float)fVar4;
    fVar5 = param_2;
    if (param_4 != 0.0) {
      fVar5 = (param_2 * _DAT_6f95a588) / _DAT_6f95a58c;
    }
    fVar4 = (float10)FUN_6f3426a0(fVar5);
    pfVar2 = &fStack_3c;
    fStack_3c = (float)fVar4;
    fStack_40 = param_1;
    goto LAB_6f345bf0;
  case 7.00649e-45:
    FUN_6f045740(&uStack_44);
    fVar4 = (float10)FUN_6f3426a0(uStack_44);
    param_1 = (float)fVar4;
    fVar5 = param_2;
    if (param_4 != 0.0) {
      fVar5 = (param_2 * _DAT_6f95a588) / _DAT_6f95a58c;
    }
    fVar4 = (float10)FUN_6f3426a0(fVar5);
    pfVar2 = &fStack_48;
    fStack_48 = (float)fVar4;
LAB_6f345bf0:
    pfVar2 = (float *)FUN_6f11fe70(pfVar2);
    fVar5 = *pfVar2;
    break;
  case 8.40779e-45:
    FUN_6f03adf0(&fStack_c);
    fVar5 = param_2 - fStack_c;
    break;
  case 9.80909e-45:
    FUN_6f03adf0(&fStack_8);
    fVar5 = param_2 - fStack_8;
    break;
  case 1.12104e-44:
    FUN_6f03adf0(&fStack_1c);
    fVar5 = param_2 - fStack_1c;
    break;
  case 1.26117e-44:
    FUN_6f045740(&fStack_18);
    fVar4 = (float10)FUN_6f3426a0(fStack_18);
    param_1 = (float)fVar4;
    fVar5 = param_2;
    if (param_4 != 0.0) {
      fVar5 = (param_2 * _DAT_6f95a588) / _DAT_6f95a58c;
    }
    fVar4 = (float10)FUN_6f3426a0(fVar5);
    fVar5 = (float)(fVar4 - (float10)param_1);
    param_2 = fVar5;
  }
  FUN_6f341600(fVar1,param_3,fVar5 / param_3);
  return;
}


