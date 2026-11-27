#!/usr/bin/env python3
"""
Tests of pytunia's one extension of Jasmin: class names can be written
with dots ("java.lang.Object") wherever they can be written with slashes
("java/lang/Object"), also inside descriptors ("Ljava.lang.String;").

Jasmin 2.4 converts the dots only in some places (e.g. in ".super" and in
the signatures of methods) and copies them into the class file everywhere
else.  The expected results in expected/ come from jasmin.jar, so this
extension is tested here: a source with dots must give the same class
file as the same source with slashes.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import pytunia  # noqa


# Every construct that contains a class name or a descriptor.  The source
# contains no other slashes, so writing all of them as dots must not change
# the class file.
SOURCE = """\
.bytecode 50.0
.class public pkg/Dots
.super java/lang/Object
.implements java/lang/Runnable
.enclosing method pkg/Outer
.annotation visible Ltest/Vis;
  cls c = "Ljava/lang/String;"
  cls2 c = Ljava/lang/Object;
  en e Ltest/Color; = RED
  ae [e Ltest/Color; = RED GREEN
  nested @ Ltest/Inner; = .annotation
    x I = 10
  .end annotation
.end annotation
.inner class public static Inner inner pkg/Dots$Inner outer pkg/Dots

.field public out Ljava/io/PrintStream;
.field public static names [Ljava/lang/String;
  .deprecated
.end field

.method public <init>()V
  .limit stack 1
  aload_0
  invokespecial java/lang/Object/<init>()V
  return
.end method

.method public run(Ljava/lang/String;)V
  .limit stack 4
  .limit locals 3
  .throws java/io/IOException
  .var 0 is this Lpkg/Dots; from L1 to L2
  .var 1 is s Ljava/lang/String;
  .var 2 is o Ljava/lang/Object; from 0 to 1
  .catch java/lang/Exception from L1 to L2 using L3
L1:
  new java/lang/Object
  dup
  invokespecial java/lang/Object/<init>()V
  checkcast java/lang/Object
  instanceof java/lang/String
  pop
  ldc java/lang/String
  ldc_w java/lang/Integer
  pop2
  iconst_1
  anewarray java/lang/String
  pop
  iconst_1
  iconst_1
  multianewarray [[Ljava/lang/String; 2
  pop
  getstatic java/lang/System/out Ljava/io/PrintStream;
  invokevirtual java/io/PrintStream/println()V
  aload_0
  aload_0
  getfield pkg/Dots/out Ljava/io/PrintStream;
  putfield pkg/Dots/out Ljava/io/PrintStream;
  aconst_null
  putstatic pkg/Dots/names [Ljava/lang/String;
  aconst_null
  invokeinterface java/util/List/size()I 1
  pop
  invokestatic java/lang/System/nanoTime()J
  pop2
L2:
  return
L3:
  .stack
    locals Object pkg/Dots
    stack Object java/lang/Throwable
  .end stack
  athrow
.end method

.method public abstract color()Ltest/Color;
  .annotation default
    e Ltest/Color; = BLUE
  .end annotation
.end method
"""


class TestDots(unittest.TestCase):

    def test_dots_give_the_same_class_file_as_slashes(self):
        name, data = pytunia.assemble_string(SOURCE)
        dotted = SOURCE.replace("/", ".")
        self.assertNotIn("/", dotted)
        dotted_name, dotted_data = pytunia.assemble_string(dotted)
        self.assertEqual(name, "pkg/Dots")
        self.assertEqual(dotted_name, name)
        self.assertEqual(dotted_data, data)

    def test_no_dots_reach_the_class_file(self):
        _, data = pytunia.assemble_string(SOURCE.replace("/", "."))
        for prefix in (b"java.", b"pkg.", b"test."):
            self.assertNotIn(prefix, data)

    def test_generic_signatures_keep_their_dots(self):
        # In a generic signature, a dot separates the name of an inner
        # class, so it must not become a slash.
        source = ('.class public G\n'
                  '.super java.lang.Object\n'
                  '.field public f Lpkg.Outer$Inner; '
                  'signature "Lpkg/Outer<TT;>.Inner;"\n')
        _, data = pytunia.assemble_string(source)
        self.assertIn(b"Lpkg/Outer$Inner;", data)
        self.assertIn(b"Lpkg/Outer<TT;>.Inner;", data)


if __name__ == "__main__":
    unittest.main()
