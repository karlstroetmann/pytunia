; tableswitch / lookupswitch in all variants, padding at all offsets
.class public Switches
.super java/lang/Object

.method public static t1(I)I
  .limit stack 2
  .limit locals 1
  iload_0
  tableswitch 0
    L0
    L1
    L2
    default : LD
L0:
  iconst_0
  ireturn
L1:
  iconst_1
  ireturn
L2:
  iconst_2
  ireturn
LD:
  iconst_m1
  ireturn
.end method

.method public static t2(I)I
  .limit stack 2
  .limit locals 1
  iload_0
  nop
  tableswitch -1 1
    L0
    L1
    L2
    default : LD
L0:
L1:
L2:
LD:
  iconst_0
  ireturn
.end method

.method public static t3(I)I
  .limit stack 2
  .limit locals 1
  iload_0
  nop
  nop
  tableswitch 10 12
    20
    30
    40
    default : 50
  lookupswitch
    1 : 20
    2 : 30
    default : 40
  ireturn
.end method

.method public static t4(I)I
  .limit stack 2
  .limit locals 1
  iload_0
  nop
  nop
  nop
  lookupswitch
    -5 : La
    0 : Lb
    100000 : La
    default : Lb
La:
  iconst_0
  ireturn
Lb:
  iconst_1
  ireturn
.end method

.method public static t5(I)I
  .limit stack 2
  .limit locals 1
  iload_0
  lookupswitch
    1 : Lx
    default : Lx
Lx:
  iconst_0
  ireturn
.end method
