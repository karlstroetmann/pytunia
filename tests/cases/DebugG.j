; ARGS: -g
.class public DebugG
.super java/lang/Object

.method public static main([Ljava/lang/String;)V
  .limit stack 2
  .limit locals 3
  .throws java/io/IOException
  .throws java.lang.Exception
  .var 0 is args [Ljava/lang/String; from L1 to L2
  .var 1 is x I
  .var 2 is list Ljava/util/List; signature "Ljava/util/List<Ljava/lang/String;>;" from L1 to L2
  .var 1 is y I from 0 to 5
  .var 2 is z Ljava/util/List; signature "Ljava/util/List<*>;" from 1 to 4
  .catch java/lang/Exception from L1 to L2 using L3
  .catch all from L1 to L2 using L3
  .catch java.lang.Error from 0 to 4 using 5
L1:
  .line 10
  iconst_0
  istore_1
  .line 11
  iinc 1 1
L2:
  return
L3:
  .line 20
  astore_2
  return
.end method

.method public static nocode()V
  .throws java/lang/Throwable
  .var 0 is a I
.end method
