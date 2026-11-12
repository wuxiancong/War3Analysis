

undefined4 __thiscall FUN_6f3a30d0(int param_1,int param_2)

{
  int iVar1;
  
  iVar1 = FUN_6f09ba70(param_2);
  if (iVar1 != 0) {
    return 1;
  }
  if ((*(uint *)(param_1 + 0x60c) & *(uint *)(param_2 + 0x14)) != 0) {
    *(undefined4 *)(param_1 + 0x60c) = 0;
    FUN_6f0bc8d0(0);
  }
  return 0;
}



### SEED 0x6f3a2fa0
  (no xrefs-to)

