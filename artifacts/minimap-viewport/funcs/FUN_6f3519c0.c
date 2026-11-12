

undefined4 __thiscall FUN_6f3519c0(int param_1,int param_2)

{
  uint uVar1;
  int *piVar2;
  int iVar3;
  undefined4 uVar4;
  
  uVar1 = *(uint *)(param_2 + 8);
  if (uVar1 < 0x10066) {
    if (uVar1 < 0x10064) {
      switch(uVar1) {
      case 0:
        uVar4 = FUN_6f351690();
        return uVar4;
      case 1:
        uVar4 = FUN_6f3515c0();
        return uVar4;
      case 2:
        uVar4 = FUN_6f3514d0();
        return uVar4;
      case 3:
        uVar4 = FUN_6f353180();
        return uVar4;
      case 4:
        uVar4 = FUN_6f353530();
        return uVar4;
      case 5:
        uVar4 = FUN_6f353330();
        return uVar4;
      case 6:
        uVar4 = FUN_6f353370();
        return uVar4;
      case 7:
        uVar4 = FUN_6f351f50();
        return uVar4;
      case 8:
        uVar4 = FUN_6f352000();
        return uVar4;
      case 9:
        uVar4 = FUN_6f351fb0();
        return uVar4;
      case 10:
        uVar4 = FUN_6f3535c0();
        return uVar4;
      case 0xb:
        uVar4 = FUN_6f353560();
        return uVar4;
      case 0xc:
        uVar4 = FUN_6f3531b0();
        return uVar4;
      case 0xd:
        uVar4 = FUN_6f352050();
        return uVar4;
      case 0xe:
        uVar4 = FUN_6f351f40();
        return uVar4;
      case 0xf:
        uVar4 = FUN_6f353220();
        return uVar4;
      case 0x10:
        uVar4 = FUN_6f3532c0();
        return uVar4;
      case 0x11:
        uVar4 = FUN_6f353300();
        return uVar4;
      case 0x12:
        uVar4 = FUN_6f353280();
        return uVar4;
      case 0x13:
        uVar4 = FUN_6f353320();
        return uVar4;
      case 0x14:
        uVar4 = FUN_6f353310();
        return uVar4;
      case 0x15:
        uVar4 = FUN_6f353040();
        return uVar4;
      case 0x16:
        uVar4 = FUN_6f353090();
        return uVar4;
      case 0x17:
        uVar4 = FUN_6f352d30();
        return uVar4;
      case 0x18:
        uVar4 = FUN_6f352fe0();
        return uVar4;
      case 0x19:
        uVar4 = FUN_6f352dc0();
        return uVar4;
      case 0x1a:
        uVar4 = FUN_6f352fa0();
        return uVar4;
      case 0x1b:
        uVar4 = FUN_6f351ec0();
        return uVar4;
      case 0x1c:
        goto LAB_6f351c70;
      case 0x1d:
        uVar4 = FUN_6f353490();
        return uVar4;
      case 0x1e:
        iVar3 = (*(int **)(param_1 + 0x400))[0x2b];
        *(uint *)(param_1 + 0x180) = (*(int *)(param_1 + 0x180) == 2) + 3;
        if ((char)iVar3 != -1) {
          (**(code **)(**(int **)(param_1 + 0x400) + 0xd0))();
        }
        return 1;
      case 0x1f:
        uVar4 = FUN_6f351290();
        return uVar4;
      case 0x20:
        uVar4 = FUN_6f353450();
        return uVar4;
      default:
        return 1;
      }
    }
  }
  else if (uVar1 < 0x1a0069) {
    if (uVar1 != 0x1a0068) {
      if (uVar1 < 0x5006f) {
        if (uVar1 != 0x5006e) {
          if (0x50065 < uVar1) {
            return 1;
          }
          if (uVar1 < 0x50064) {
            if (uVar1 < 0x30064) {
              return 1;
            }
            if (0x30067 < uVar1) {
              return 1;
            }
          }
        }
      }
      else {
        if (0x1a0065 < uVar1) {
          return 1;
        }
        if (uVar1 < 0x1a0064) {
          if (uVar1 < 0xf0101) {
            return 1;
          }
          if (0xf0102 < uVar1) {
            return 1;
          }
        }
      }
    }
  }
  else {
    if (0x40060064 < uVar1) {
      if (uVar1 == 0x40060066) {
        uVar4 = FUN_6f352790();
        return uVar4;
      }
      if (uVar1 != 0x40060067) {
        return 1;
      }
      uVar4 = FUN_6f3512d0();
      return uVar4;
    }
    if (uVar1 == 0x40060064) {
      uVar4 = FUN_6f3520f0();
      return uVar4;
    }
    if (uVar1 == 0x40040065) {
      uVar4 = FUN_6f351d50();
      return uVar4;
    }
    if (uVar1 != 0x400500c9) {
      return 1;
    }
  }
  if (*(int *)(param_1 + 0x1ac) == 0) {
    return 0;
  }
  if (*(int **)(param_1 + 0x1b4) == (int *)0x0) {
    return 1;
  }
                    /* WARNING: Could not recover jumptable at 0x6f351bb2. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  uVar4 = (**(code **)(**(int **)(param_1 + 0x1b4) + 0xc))();
  return uVar4;
LAB_6f351c70:
  if (*(char *)(*(int *)(param_1 + 0x41c) + 0xac) != -1) {
    (**(code **)(**(int **)(param_1 + 0x3f4) + 0xd0))();
    (**(code **)(**(int **)(param_1 + 0x41c) + 0xd0))();
    return 1;
  }
  FUN_6f354fc0(0);
  iVar3 = *(int *)(param_1 + 0x3c0);
  *(undefined4 *)(iVar3 + 0x624) = 1;
  *(undefined4 *)(iVar3 + 0x61c) = 1;
  (**(code **)(**(int **)(param_1 + 0x3f4) + 0xd4))();
  piVar2 = *(int **)(param_1 + 0x3ec);
  piVar2[0x24] = 1;
  (**(code **)(*piVar2 + 0x68))();
  piVar2 = *(int **)(param_1 + 0x3f0);
  piVar2[0x24] = 1;
  (**(code **)(*piVar2 + 0x68))();
  piVar2 = *(int **)(param_1 + 0x3e4);
  piVar2[0x24] = 1;
  (**(code **)(*piVar2 + 0x68))();
  if (*(int *)(param_1 + 0x3ac) != 0) {
    FUN_6f356bf0(*(int *)(param_1 + 0x3ac));
  }
  if (*(int *)(param_1 + 0x3a8) != 0) {
    FUN_6f356900(*(int *)(param_1 + 0x3a8));
  }
  return 1;
}


