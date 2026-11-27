#!/usr/bin/env python3
"""
Tests of pytunia's extension "Types in Java notation": types can be
written as in Java, with fully qualified class names, e.g.

    .method public static main(java.lang.String[]) void
    getstatic java.lang.System.out java.io.PrintStream

instead of the descriptors of the JVM.  Jasmin does not know this
notation, so the expected results come from the same source written with
descriptors.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import pytunia  # noqa
from pytunia.javatypes import (class_operand, field_descriptor,  # noqa
                               method_descriptor)


# the same class, written with the descriptors of the JVM ...
DESCRIPTORS = """\
.bytecode 50.0
.class public pkg/Types
.super java/lang/Object
.enclosing method pkg/Outer/m(I[Ljava/lang/String;)V

.field public out Ljava/io/PrintStream;
.field public static grid [[I
.field public big J
  .deprecated
.end field

.method public <init>()V
  .limit stack 1
  aload_0
  invokespecial java/lang/Object/<init>()V
  return
.end method

.method public static main([Ljava/lang/String;)V
  .limit stack 4
  .limit locals 2
  .var 0 is args [Ljava/lang/String; from L1 to L2
  .var 1 is n I
L1:
  getstatic java/lang/System/out Ljava/io/PrintStream;
  ldc "Hello"
  invokevirtual java/io/PrintStream/println(Ljava/lang/String;)V
  iconst_1
  iconst_2
  invokestatic pkg/Types/max(II)I
  pop
  aconst_null
  checkcast [I
  instanceof [Ljava/lang/String;
  pop
  ldc [Ljava/lang/Object;
  pop
  iconst_1
  anewarray [D
  pop
  iconst_1
  iconst_1
  multianewarray [[Ljava/lang/String; 2
  putstatic pkg/Types/grid [[I
  aconst_null
  ldc "x"
  iconst_0
  invokeinterface java/util/List/set(ILjava/lang/Object;)Ljava/lang/Object; 3
  pop
L2:
  return
.end method

.method public static max(II)I
  .limit stack 2
  .limit locals 2
  iload_0
  iload_1
  if_icmpge L1
  iload_1
  ireturn
L1:
  .stack
    locals Integer
    locals Integer
    stack Object [Ljava/lang/String;
  .end stack
  iload_0
  ireturn
.end method

.method public abstract many(ZBCSJFD[[ZLjava/util/Map$Entry;)[Ljava/lang/Object;
.end method
"""

# ... and in Java notation (with blanks of all kinds in the signatures)
JAVA = """\
.bytecode 50.0
.class public pkg.Types
.super java.lang.Object
.enclosing method pkg.Outer.m(int, java.lang.String[]) void

.field public out java.io.PrintStream
.field public static grid int[][]
.field public big long
  .deprecated
.end field

.method public <init>() void
  .limit stack 1
  aload_0
  invokespecial java.lang.Object.<init>() void
  return
.end method

.method public static main(java.lang.String[]) void
  .limit stack 4
  .limit locals 2
  .var 0 is args java.lang.String[] from L1 to L2
  .var 1 is n int
L1:
  getstatic java.lang.System.out java.io.PrintStream
  ldc "Hello"
  invokevirtual java.io.PrintStream.println(java.lang.String) void
  iconst_1
  iconst_2
  invokestatic pkg.Types.max(int,int)int
  pop
  aconst_null
  checkcast int[]
  instanceof java.lang.String[]
  pop
  ldc java.lang.Object[]
  pop
  iconst_1
  anewarray double[]
  pop
  iconst_1
  iconst_1
  multianewarray java.lang.String[][] 2
  putstatic pkg.Types.grid int[][]
  aconst_null
  ldc "x"
  iconst_0
  invokeinterface java.util.List.set( int , java.lang.Object )  java.lang.Object 3
  pop
L2:
  return
.end method

.method public static max(int, int) int
  .limit stack 2
  .limit locals 2
  iload_0
  iload_1
  if_icmpge L1
  iload_1
  ireturn
L1:
  .stack
    locals Integer
    locals Integer
    stack Object java.lang.String[]
  .end stack
  iload_0
  ireturn
.end method

.method public abstract many(boolean, byte, char, short, long, float, double, boolean[][], java.util.Map$Entry) java.lang.Object[]
.end method
"""


class TestJavaTypes(unittest.TestCase):

    def test_java_notation_gives_the_same_class_file(self):
        name, data = pytunia.assemble_string(DESCRIPTORS)
        java_name, java_data = pytunia.assemble_string(JAVA)
        self.assertEqual(java_name, name)
        self.assertEqual(java_data, data)

    def test_field_descriptors(self):
        for java, descriptor in [
                ("int", "I"), ("boolean", "Z"), ("long[]", "[J"),
                ("java.lang.String", "Ljava/lang/String;"),
                ("java/lang/String", "Ljava/lang/String;"),
                ("Sum", "LSum;"), ("java.util.Map$Entry[][]",
                                   "[[Ljava/util/Map$Entry;"),
                # descriptors keep their meaning
                ("I", "I"), ("[I", "[I"), ("Ljava.lang.String;",
                                           "Ljava/lang/String;"),
                # neither: left as it is (as by Jasmin)
                ("void", "void"), ("int[", "int["), ("a b", "a b")]:
            with self.subTest(java=java):
                self.assertEqual(field_descriptor(java), descriptor)

    def test_method_descriptors(self):
        for java, descriptor in [
                ("(java.lang.String[]) void", "([Ljava/lang/String;)V"),
                ("(java.lang.String[])void", "([Ljava/lang/String;)V"),
                ("() int", "()I"), ("(int, int) int", "(II)I"),
                ("(int,long)double[]", "(IJ)[D"),
                ("(Sum) Sum", "(LSum;)LSum;"),
                # descriptors keep their meaning, also when mixed
                ("(II)I", "(II)I"), ("(IJ)V", "(IJ)V"),
                ("([Ljava/lang/String;)V", "([Ljava/lang/String;)V"),
                ("(java.lang.String[], I) V", "([Ljava/lang/String;I)V"),
                # malformed without blanks: left as it is (as by Jasmin)
                ("(foo-bar)V", "(foo-bar)V"), ("(I)", "(I)")]:
            with self.subTest(java=java):
                self.assertEqual(method_descriptor(java), descriptor)

    def test_class_operands(self):
        for java, operand in [
                ("java.lang.String", "java/lang/String"),
                ("java.lang.String[]", "[Ljava/lang/String;"),
                ("int[][]", "[[I"), ("[I", "[I"),
                ("[Ljava/lang/String;", "[Ljava/lang/String;")]:
            with self.subTest(java=java):
                self.assertEqual(class_operand(java), operand)

    def test_malformed_signature_with_blanks(self):
        source = ('.class public X\n'
                  '.super java.lang.Object\n'
                  '.method public static m(int, foo bar) void\n'
                  '  return\n'
                  '.end method\n')
        with self.assertRaises(pytunia.AssemblyError) as cm:
            pytunia.assemble_string(source)
        error = cm.exception.errors[0]
        self.assertEqual(error.line, 3)
        self.assertIn("malformed method signature", error.message)

    def test_words_are_not_joined_across_lines(self):
        source = ('.class public X\n'
                  '.super java.lang.Object\n'
                  '.method public static m(int,\n'
                  '  int) void\n'
                  '  return\n'
                  '.end method\n')
        with self.assertRaises(pytunia.AssemblyError) as cm:
            pytunia.assemble_string(source)
        self.assertEqual(cm.exception.errors[0].line, 4)

    def test_other_words_are_not_joined(self):
        # Outside of method signatures, words are not joined: this is a
        # field with the (strange, but legal) name "f()" and the type int.
        source = ('.class public X\n'
                  '.super java.lang.Object\n'
                  '.field public f() int\n')
        _, data = pytunia.assemble_string(source)
        self.assertIn(b"\x00\x03f()", data)
        self.assertNotIn(b"f() int", data)


if __name__ == "__main__":
    unittest.main()
