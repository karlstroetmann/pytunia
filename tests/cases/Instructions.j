; all kinds of instruction arguments
.class public Instructions
.super java/lang/Object

.method public test([Ljava/lang/String;)I
  .limit stack 20
  .limit locals 400
  nop
  aconst_null
  pop
  iconst_m1
  iconst_0
  iconst_1
  iconst_2
  iconst_3
  iconst_4
  iconst_5
  lconst_0
  lconst_1
  fconst_0
  fconst_1
  fconst_2
  dconst_0
  dconst_1
  bipush 127
  bipush -128
  sipush 32767
  sipush -32768
  iload 1
  iload 255
  iload 256
  iload_w 3
  lload 4
  lload_w 4
  fload 6
  fload_w 6
  dload 7
  dload_w 7
  aload 9
  aload_w 9
  istore 300
  istore_w 2
  lstore 10
  lstore_w 10
  fstore 12
  fstore_w 12
  dstore 13
  dstore_w 13
  astore 15
  astore_w 15
  iload_0
  iload_1
  iload_2
  iload_3
  lload_0
  lload_1
  lload_2
  lload_3
  fload_0
  fload_1
  fload_2
  fload_3
  dload_0
  dload_1
  dload_2
  dload_3
  aload_0
  aload_1
  aload_2
  aload_3
  istore_0
  istore_1
  istore_2
  istore_3
  lstore_0
  lstore_1
  lstore_2
  lstore_3
  fstore_0
  fstore_1
  fstore_2
  fstore_3
  dstore_0
  dstore_1
  dstore_2
  dstore_3
  astore_0
  astore_1
  astore_2
  astore_3
  iaload
  laload
  faload
  daload
  aaload
  baload
  caload
  saload
  iastore
  lastore
  fastore
  dastore
  aastore
  bastore
  castore
  sastore
  pop
  pop2
  dup
  dup_x1
  dup_x2
  dup2
  dup2_x1
  dup2_x2
  swap
  iadd
  ladd
  fadd
  dadd
  isub
  lsub
  fsub
  dsub
  imul
  lmul
  fmul
  dmul
  idiv
  ldiv
  fdiv
  ddiv
  irem
  lrem
  frem
  drem
  ineg
  lneg
  fneg
  dneg
  ishl
  lshl
  ishr
  lshr
  iushr
  lushr
  iand
  land
  ior
  lor
  ixor
  lxor
  iinc 1 1
  iinc 1 127
  iinc 1 -128
  iinc 1 -129
  iinc 300 5
  iinc_w 2 3
  i2l
  i2f
  i2d
  l2i
  l2f
  l2d
  f2i
  f2l
  f2d
  d2i
  d2l
  d2f
  i2b
  i2c
  i2s
  int2byte
  int2char
  int2short
  lcmp
  fcmpl
  fcmpg
  dcmpl
  dcmpg
Lbranch:
  ifeq Lbranch
  ifne Lbranch
  iflt Lbranch
  ifge Lbranch
  ifgt Lbranch
  ifle Lbranch
  if_icmpeq Lbranch
  if_icmpne Lbranch
  if_icmplt Lbranch
  if_icmpge Lbranch
  if_icmpgt Lbranch
  if_icmple Lbranch
  if_acmpeq Lbranch
  if_acmpne Lbranch
  ifnull Lforward
  ifnonnull Lforward
  goto Lforward
  jsr Lforward
  goto_w Lbranch
  jsr_w Lforward
  goto $+3
  goto $-3
  ifeq $+0x10
  goto_w $+5
  bipush $+5
  ret 1
  ret 300
  ret_w 2
Lforward:
  getstatic java/lang/System/out Ljava/io/PrintStream;
  putstatic Instructions/x I
  getfield Instructions.y J
  putfield Instructions/y J
  invokevirtual java/io/PrintStream/println(Ljava/lang/String;)V
  invokespecial java/lang/Object/<init>()V
  invokenonvirtual java/lang/Object/<init>()V
  invokestatic java.lang.Math.abs(I)I
  invokeinterface java/util/List/size()I 1
  invokedynamic java/lang/Foo/bar()V
  new java/lang/Object
  newarray boolean
  newarray char
  newarray float
  newarray double
  newarray byte
  newarray short
  newarray int
  newarray long
  anewarray java/lang/String
  anewarray [I
  multianewarray [[I 2
  arraylength
  athrow
  checkcast java/lang/String
  checkcast [Ljava/lang/Object;
  instanceof java/lang/String
  monitorenter
  monitorexit
  breakpoint
  ireturn
  lreturn
  freturn
  dreturn
  areturn
  return
.end method

.method public abstract abs()V
.end method

.method public native nat(II)J
.end method
