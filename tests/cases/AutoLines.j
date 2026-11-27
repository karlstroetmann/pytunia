; ARGS: -g
.class public AutoLines
.super java/lang/Object

.method public static m(I)I
  .limit stack 2
  .limit locals 1

  iload_0     ; comment
  ifeq Lz
  iload_0
  tableswitch 0
    La
    default : Lz
La:
  lookupswitch
    1 : Lz
    default : Lz
Lz:
  ldc "x"
  pop
  goto $+3
  iconst_0
  ireturn
.end method
