

void FUN_6f3a0920(int param_1)

{
  uint uVar1;
  
  uVar1 = *(uint *)(param_1 + 8);
  if (uVar1 < 0x1a0066) {
    if (uVar1 == 0x1a0065) {
      FUN_6f3a0fa0();
      return;
    }
    if (uVar1 == 0x10064) {
      FUN_6f3a4aa0();
      return;
    }
    if (uVar1 == 0x1a0064) {
      FUN_6f3a5df0();
      return;
    }
  }
  else {
    if (uVar1 == 0x1a0068) {
      FUN_6f3a6ac0();
      return;
    }
    if (uVar1 == 0x40060064) {
      FUN_6f3a1f00();
      return;
    }
  }
  FUN_6f3a0250();
  return;
}


