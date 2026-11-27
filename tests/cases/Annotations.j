; annotations on classes, fields, methods and parameters; annotation defaults
.bytecode 49.0
.class public Annotations
.super java/lang/Object
.annotation visible Ltest/Vis;
  i I = 1
  b B = -128
  c C = 65535
  s S = 32767
  z Z = 1
  f F = 1.5
  d D = 2.5d
  d2 D = 2.5
  j J = 123456789012
  j2 J = 5
  str s = "hello"
  str2 s = word
  cls c = "Ljava/lang/String;"
  en e Ltest/Color; = RED
  ai [I = 1 2 3
  as [s = "a" "b"
  ae [e Ltest/Color; = RED GREEN
  nested @ Ltest/Inner; = .annotation
    x I = 10
    y s = "y"
  .end annotation
  na [@ Ltest/Inner; = .annotation
    x I = 1
  .end annotation
  .annotation
    x I = 2
    deeper @ Ltest/Deep; = .annotation
      q Z = 0
    .end annotation
  .end annotation
.end annotation
.annotation invisible Ltest/Invis;
.end annotation
.annotation visible java.lang.Deprecated
.end annotation

.field public f I
  .annotation visible Ltest/FA;
    v I = 1
  .end annotation
  .annotation invisible Ltest/FB;
  .end annotation
.end field

.method public m(II)V
  .annotation visible Ltest/MA;
    v I = 1
  .end annotation
  .annotation invisible Ltest/MB;
  .end annotation
  .annotation invisibleparam 2 Ltest/PA;
    v s = "p"
  .end annotation
  .annotation visibleparam 1 Ltest/PB;
  .end annotation
  .annotation visibleparam 1 Ltest/PC;
  .end annotation
  .annotation visibleparam 3 Ltest/PD;
  .end annotation
  .limit stack 1
  return
.end method

.method public abstract value()I
  .annotation default
    I = 42
  .end annotation
.end method

.method public abstract arr()[Ljava/lang/String;
  .annotation default
    [s = "x" "y"
  .end annotation
.end method

.method public abstract en()Ltest/Color;
  .annotation default
    e Ltest/Color; = BLUE
  .end annotation
.end method

.method public abstract ann()Ltest/Inner;
  .annotation default
    @ Ltest/Inner; = .annotation
      x I = 3
    .end annotation
  .end annotation
.end method
