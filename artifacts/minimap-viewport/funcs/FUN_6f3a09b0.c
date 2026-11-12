

void FUN_6f3a09b0(int param_1)

{
  uint uVar1;
  
  uVar1 = *(uint *)(param_1 + 8);
  if (uVar1 < 0x1a0065) {
    if (uVar1 == 0x1a0064) {
      FUN_6f3a5e20();
      return;
    }
    if (uVar1 < 0x30066) {
      if (uVar1 == 0x30065) {
        FUN_6f3a1aa0();
        return;
      }
      if (uVar1 == 0x10064) {
        FUN_6f3a4af0();
        return;
      }
      if (uVar1 == 0x30064) {
        FUN_6f39f3e0();
        return;
      }
    }
    else {
      if (uVar1 == 0x50064) {
        FUN_6f3a5530();
        return;
      }
      if (uVar1 == 0x50065) {
        FUN_6f3a1920();
        return;
      }
    }
  }
  else if (uVar1 < 0x40060065) {
    if (uVar1 == 0x40060064) {
      FUN_6f3a1f30();
      return;
    }
    switch(uVar1) {
    case 0x1a0065:
      FUN_6f3a0fd0();
      return;
    case 0x1a0066:
      FUN_6f3a5e40();
      return;
    case 0x1a0067:
      FUN_6f3a1620();
      return;
    case 0x1a0068:
      FUN_6f3a6af0();
      return;
    }
  }
  else if (uVar1 == 0x40060066) {
    FUN_6f3a20a0();
    return;
  }
  FUN_6f3a0250();
  return;
}


