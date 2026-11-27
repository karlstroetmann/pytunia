; ARGS: -g
.class public NumLabelsG
.super java/lang/Object

.method public static m(I)I
  .limit stack 2
  .limit locals 1
  0: iload_0
  1: ifeq 8
  4: iconst_1
  5: goto 9
  8: iconst_0
  9: ireturn
.end method

.method public static n()V
  goto $+3
  return
.end method

.method public static o()V
  .limit stack 1
  iconst_0
  10: pop
  return
  '20':
  nop
  20: return
.end method
