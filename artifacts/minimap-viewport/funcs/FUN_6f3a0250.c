

undefined4 FUN_6f3a0250(int param_1)

{
  undefined4 uVar1;
  undefined4 uVar2;
  
  if (*(int *)(param_1 + 8) == 0x10065) {
    uVar1 = *(undefined4 *)(param_1 + 0x18);
    uVar2 = *(undefined4 *)(param_1 + 0x14);
    FUN_6f398520(uVar2,uVar1);
    FUN_6f34daa0(uVar2,uVar1);
    return 1;
  }
  if (*(int *)(param_1 + 8) != 0x50064) {
    return 0;
  }
  uVar1 = FUN_6f3a54f0();
  return uVar1;
}


