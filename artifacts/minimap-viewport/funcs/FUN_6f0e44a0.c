

undefined4 * __fastcall FUN_6f0e44a0(undefined4 *param_1)

{
  undefined4 *puVar1;
  int iVar2;
  
  *param_1 = 0;
  iVar2 = 2;
  puVar1 = param_1 + 3;
  do {
    puVar1[-2] = 0;
    *puVar1 = 0;
    iVar2 = iVar2 + -1;
    puVar1 = puVar1 + 1;
  } while (iVar2 != 0);
  param_1[5] = 0;
  return param_1;
}


