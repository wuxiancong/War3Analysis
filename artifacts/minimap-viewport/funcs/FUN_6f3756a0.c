

undefined4 FUN_6f3756a0(int param_1)

{
  uint uVar1;
  char cVar2;
  undefined4 uVar3;
  
  cVar2 = FUN_6f30df40();
  if (cVar2 != -1) {
    return 1;
  }
  uVar1 = *(uint *)(param_1 + 8);
  if (uVar1 < 0x5006f) {
    if (uVar1 == 0x5006e) {
      uVar3 = FUN_6f377cf0(param_1);
      return uVar3;
    }
    if (uVar1 < 0x30065) {
      if (uVar1 == 0x30064) {
        uVar3 = FUN_6f375500(param_1);
        return uVar3;
      }
      if (uVar1 == 0x10064) {
        uVar3 = FUN_6f376d70(param_1);
        return uVar3;
      }
    }
    else if (uVar1 < 0x30068) {
      if (uVar1 == 0x30067) {
        uVar3 = FUN_6f375220(param_1);
        return uVar3;
      }
      if (uVar1 == 0x30065) {
        uVar3 = FUN_6f376170(param_1);
        return uVar3;
      }
      if (uVar1 == 0x30066) {
        uVar3 = FUN_6f377c80(param_1);
        return uVar3;
      }
    }
    else if (uVar1 == 0x50065) {
      uVar3 = FUN_6f375ca0(param_1);
      return uVar3;
    }
  }
  else if (uVar1 < 0x40060065) {
    if (uVar1 == 0x40060064) {
      uVar3 = FUN_6f376360(param_1);
      return uVar3;
    }
    switch(uVar1) {
    case 0x1a0064:
      uVar3 = FUN_6f377400(param_1);
      return uVar3;
    case 0x1a0065:
      uVar3 = FUN_6f375810(param_1);
      return uVar3;
    case 0x1a0066:
      uVar3 = FUN_6f3775c0(param_1);
      return uVar3;
    case 0x1a0067:
      uVar3 = FUN_6f375a60(param_1);
      return uVar3;
    case 0x1a0068:
      uVar3 = FUN_6f377b90(param_1);
      return uVar3;
    }
  }
  else if (uVar1 == 0x40060066) {
    uVar3 = FUN_6f376c60(param_1);
    return uVar3;
  }
  uVar3 = FUN_6f3a0250(param_1);
  return uVar3;
}


