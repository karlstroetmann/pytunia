; StackMapTable frames (class file version >= 50)
.bytecode 50.0
.class public StackMapTable
.super java/lang/Object

.method public <init>()V
  .limit stack 1
  .limit locals 1
  aload_0
  invokespecial java/lang/Object/<init>()V
  return
.end method

.method public static m(I)I
  .limit stack 3
  .limit locals 3
  iload_0
  ifeq L1
  iconst_1
  istore_1
  goto L2
L1:
  .stack
    locals Integer
  .end stack
  iconst_0
  istore_1
L2:
  .stack
    offset L2
    locals Integer
    locals Integer
  .end stack
  iload_1
  ireturn
.end method

; all frame types
.method public static frames(IJ)V
  .limit stack 4
  .limit locals 10
  iconst_0
  .stack
    offset 1
    locals Integer
    locals Long
    stack Integer
  .end stack
  pop
  .stack
    offset 2
    locals Integer
    locals Long
  .end stack
  nop
  .stack use locals
    offset 3
    locals Float
    locals Double
    locals Object java/lang/String
  .end stack
  nop
  .stack use 2 locals
    offset 4
  .end stack
  nop
  .stack use 1 locals
    offset 5
    stack Null
  .end stack
  nop
  .stack
    offset 100
    locals Integer
    stack Object [I
  .end stack
  nop
  .stack
    offset 200
    locals Integer
  .end stack
  nop
  .stack
    offset 300
    locals Top
    locals UninitializedThis
    stack Integer
    stack Float
  .end stack
  nop
  .stack
    offset 400
    locals Uninitialized LNew
    locals Uninitialized 7
    stack Uninitialized 70000
  .end stack
  nop
  .stack use locals
    offset 401
  .end stack
  nop
  .stack use locals
    offset 402
    locals Integer
    locals Integer
    locals Integer
    locals Integer
  .end stack
LNew:
  new java/lang/Object
  return
.end method

; frames given out of order are sorted
.method public static unsorted()V
  .limit stack 1
  .limit locals 1
  .stack
    offset 3
    locals Integer
  .end stack
  .stack
    offset 1
  .end stack
  .stack
    offset 2
    locals Float
  .end stack
  .stack
    offset 0
  .end stack
  nop
  nop
  nop
  nop
  return
.end method
