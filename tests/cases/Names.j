; quoted names and unicode escapes in names
.class public 'class'
.super java/lang/Object

.field public 'goto' I
.field public äöü I

.method public \u0070ublic()V
  .limit stack 2
  getstatic class/goto I
  getstatic class/äöü I
  pop2
  '0x':
  goto '0x'
.end method

.method public <clinit>()V
  return
.end method
