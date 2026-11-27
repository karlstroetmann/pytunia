; class header directives, inner classes, generic attributes
.bytecode 49.0
.source Outer.java
.class public Outer$Inner
.super java/lang/Object
.implements java/lang/Runnable
.signature "<T:Ljava/lang/Object;>Ljava/lang/Object;Ljava/lang/Runnable;"
.enclosing method Outer/foo(I)V
.deprecated
.attribute ClassAttr "attr.bin"
.attribute EmptyAttr "empty.bin"
.debug "SMAP\nOuter.java\n"
.debug "*E\n"
.inner class public static Inner inner Outer$Inner outer Outer
.inner interface private Iface inner Outer$Iface outer Outer
.inner class inner Outer$1
.inner class
.inner class abstract final Anon

.field public x I
  .attribute FieldAttr "attr.bin"
.end field

.method public run()V
  .attribute MethodAttr "attr.bin"
  .signature "()V"
  .deprecated
.end method

.method public code()V
  .limit stack 0
  return
  .attribute CodeAttr "attr.bin"
.end method
