

void FUN_6f3c2c60(int param_1)

{
  uint uVar1;
  
  uVar1 = *(uint *)(param_1 + 8);
  if (uVar1 < 0x1a0065) {
    if (uVar1 == 0x1a0064) {
      FUN_6f3c3080();
      return;
    }
    if (uVar1 == 0x10064) {
      FUN_6f3c3040();
      return;
    }
    if (uVar1 == 0x30064) {
      FUN_6f3c2b90();
      return;
    }
  }
  else if (uVar1 < 0x40060065) {
    if (uVar1 == 0x40060064) {
      FUN_6f3c2f80();
      return;
    }
    switch(uVar1) {
    case 0x1a0065:
      FUN_6f3c2d10();
      return;
    case 0x1a0066:
      FUN_6f3c3210();
      return;
    case 0x1a0067:
      FUN_6f3c2e80();
      return;
    case 0x1a0068:
      FUN_6f3c32f0();
      return;
    }
  }
  else if (uVar1 == 0x40060066) {
    FUN_6f3c2fe0();
    return;
  }
  FUN_6f3a0250();
  return;
}


