#!/usr/bin/env python3
"""
Tests for the Python port of Jasmin.

Every test case in cases/ is assembled with the Python version and the
results (class files, standard output, standard error and exit status)
are compared with the results of the Java version, which were recorded
by make_expected.py in expected/.  pytunia's error messages differ from
those of Jasmin; for the cases with errors, expected_errors.py describes
what is checked instead.

Run with:  python3 -m unittest discover -s tests     (in directory Python)
      or:  python3 tests/test_cli.py
"""

import os
import shutil
import struct
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from make_expected import EXPECTED, case_names, run_case  # noqa
from expected_errors import check_error_report  # noqa

from pytunia import javacompat  # noqa
from pytunia.javacompat import JavaHashtable, string_hash  # noqa


def python_command():
    return [sys.executable, '-m', 'pytunia']


def read_expected(name):
    target = os.path.join(EXPECTED, name)
    with open(os.path.join(target, 'stdout.txt')) as f:
        stdout = f.read()
    with open(os.path.join(target, 'stderr.txt')) as f:
        stderr = f.read()
    with open(os.path.join(target, 'status.txt')) as f:
        status = int(f.read())
    classes = {}
    cdir = os.path.join(target, 'classes')
    for root, _, files in os.walk(cdir):
        for fn in files:
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, cdir).replace(os.sep, '/')
            with open(path, 'rb') as fp:
                classes[rel] = fp.read()
    return stdout, stderr, status, classes


class AssemblerTests(unittest.TestCase):
    """Compares the Python version with the recorded Java results."""
    maxDiff = None


def _make_test(name):
    def test(self):
        if not os.path.isdir(os.path.join(EXPECTED, name)):
            self.skipTest('no expected results (run make_expected.py)')
        env = dict(os.environ)
        env['PYTHONPATH'] = ROOT + os.pathsep + env.get('PYTHONPATH', '')
        outdir = tempfile.mkdtemp()
        try:
            stdout, stderr, status, classes = run_case(
                python_command(), name, outdir, env)
        finally:
            shutil.rmtree(outdir)
        e_stdout, e_stderr, e_status, e_classes = read_expected(name)
        self.assertEqual(e_stdout, stdout, 'stdout differs')
        if e_classes:
            self.assertEqual(e_stderr, stderr, 'stderr differs')
        else:
            check_error_report(self, name, stderr)
        self.assertEqual(e_status, status, 'exit status differs')
        self.assertEqual(sorted(e_classes), sorted(classes),
                         'different class files generated')
        for rel in e_classes:
            self.assertTrue(e_classes[rel] == classes[rel],
                            'class file %s differs' % rel)
    return test


for _name in case_names():
    setattr(AssemblerTests, 'test_' + _name, _make_test(_name))


class NumberFormatTests(unittest.TestCase):
    """Float.toString / Double.toString emulation."""

    def test_numbers(self):
        path = os.path.join(EXPECTED, 'numbers.txt')
        if not os.path.exists(path):
            self.skipTest('no expected results (run make_expected.py)')
        mismatches = []
        with open(path) as f:
            for line in f:
                kind, bits, expected = line.split()
                if kind == 'F':
                    value = struct.unpack('>f', bytes.fromhex(bits))[0]
                    got = javacompat.float_to_string(value)
                else:
                    value = struct.unpack('>d', bytes.fromhex(bits))[0]
                    got = javacompat.double_to_string(value)
                if got != expected:
                    mismatches.append((kind, bits, expected, got))
        self.assertEqual(mismatches, [])


class JavaCompatTests(unittest.TestCase):
    def test_string_hash(self):
        self.assertEqual(string_hash(""), 0)
        self.assertEqual(string_hash("hello"), 99162322)
        self.assertEqual(string_hash("java/lang/Object"), 2080463411)

    def test_hashtable_order(self):
        # enumeration order of java.util.Hashtable for these keys (JDK 8)
        keys = ["Aa", "BB", "AaAa", "BBBB", "AaBB", "BBAa",
                "java/lang/Object", "Code", "<init>", "()V",
                "CLASS: #$%^#$java/lang/Object", "LineNumberTable",
                "SourceFile", "main", "([Ljava/lang/String;)V",
                "String: @#$hello", "hello", "Integer: @#$42", "Long: @#$-1",
                "Float: @#$3.14", "Double: @#$1.0E300",
                "NT : @#$%printlnSD#$(Ljava/lang/String;)V", "x", "y", "z",
                "\u00e4\u00f6\u00fc", "\ud83d\ude00", "", "a/b/c&%$#&d*()#$I",
                "StackMapTable", "Exceptions", "ConstantValue", "Signature",
                "Deprecated", "InnerClasses", "EnclosingMethod",
                "RuntimeVisibleAnnotations", "AnnotationDefault",
                "LocalVariableTable", "q1", "q2", "q3", "q4", "q5"]
        ht = JavaHashtable()
        for i, k in enumerate(keys):
            ht.put(k, i)
        self.assertEqual(ht.values(),
                         [16, 9, 13, 15, 17, 6, 2, 3, 4, 5, 34, 10, 18, 37,
                          11, 35, 31, 29, 20, 28, 43, 42, 41, 40, 39, 14, 33,
                          19, 30, 25, 12, 8, 38, 24, 23, 22, 36, 0, 1, 21, 32,
                          26, 7, 27])

    def test_parse(self):
        self.assertEqual(javacompat.parse_int("+5"), 5)
        self.assertEqual(javacompat.parse_int("-2147483648"), -2147483648)
        self.assertRaises(javacompat.JavaException, javacompat.parse_int,
                          "2147483648")
        self.assertRaises(javacompat.JavaException, javacompat.parse_int,
                          "1_000")
        self.assertEqual(javacompat.parse_double("1.5f"), 1.5)
        self.assertEqual(javacompat.parse_double("-0x1.8p1"), -3.0)
        self.assertRaises(javacompat.JavaException, javacompat.parse_double,
                          "1.5x")

    def test_modified_utf8(self):
        self.assertEqual(javacompat.modified_utf8("a\0b"), b"a\xc0\x80b")
        self.assertEqual(javacompat.modified_utf8("\ud83d\ude00"),
                         b"\xed\xa0\xbd\xed\xb8\x80")


if __name__ == '__main__':
    unittest.main()
