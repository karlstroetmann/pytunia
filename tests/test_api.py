#!/usr/bin/env python3
"""
Tests of the library interface: pytunia.assemble and
pytunia.assemble_string.

Every test case in cases/ is assembled with both functions.  The class
files must be identical to those of the Java version (expected/), and
for sources with errors str(AssemblyError) must be identical to the error
output of the Java version.
"""

import concurrent.futures
import contextlib
import io
import os
import pickle
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from make_expected import CASES, EXPECTED, case_args, case_names  # noqa
from test_cli import read_expected  # noqa

import pytunia  # noqa


def options(name):
    """(line_numbers, encoding) for the command line arguments of a case"""
    args = case_args(os.path.join(CASES, name + '.j'))
    line_numbers = '-g' in args
    encoding = args[args.index('-e') + 1] if '-e' in args else 'utf-8'
    return line_numbers, encoding


def read_source(name):
    _, encoding = options(name)
    with open(os.path.join(CASES, name + '.j'), 'rb') as f:
        return f.read().decode(encoding, 'replace')


class InCasesDirectory(unittest.TestCase):
    """Runs the tests in the directory cases (as the command line tests
    do: file names in .attribute directives are relative to it)."""

    @classmethod
    def setUpClass(cls):
        cls._old_cwd = os.getcwd()
        os.chdir(CASES)

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls._old_cwd)

    def setUp(self):
        if not os.path.isdir(EXPECTED):
            self.skipTest('no expected results (run make_expected.py)')


class AssembleTests(InCasesDirectory):
    """pytunia.assemble() on all test cases"""


class AssembleStringTests(InCasesDirectory):
    """pytunia.assemble_string() on all test cases"""


def _make_assemble_test(name):
    def test(self):
        _, e_stderr, _, e_classes = read_expected(name)
        line_numbers, encoding = options(name)
        out = tempfile.mkdtemp()
        try:
            if e_classes:
                path = pytunia.assemble(name + '.j', out,
                                        line_numbers=line_numbers,
                                        encoding=encoding)
                rel = os.path.relpath(str(path), out).replace(os.sep, '/')
                self.assertEqual([rel], list(e_classes))
                self.assertTrue(path.read_bytes() == e_classes[rel],
                                'class file differs')
            else:
                with self.assertRaises(pytunia.AssemblyError) as cm:
                    pytunia.assemble(name + '.j', out,
                                     line_numbers=line_numbers,
                                     encoding=encoding)
                self.assertEqual(str(cm.exception) + '\n', e_stderr)
                self.assertEqual(os.listdir(out), [])
        finally:
            shutil.rmtree(out)
    return test


def _make_assemble_string_test(name):
    def test(self):
        _, e_stderr, _, e_classes = read_expected(name)
        line_numbers, _ = options(name)
        source = read_source(name)
        if e_classes:
            class_name, data = pytunia.assemble_string(
                source, name + '.j', line_numbers=line_numbers)
            self.assertEqual([class_name + '.class'], list(e_classes))
            self.assertTrue(data == e_classes[class_name + '.class'],
                            'class file differs')
        else:
            with self.assertRaises(pytunia.AssemblyError) as cm:
                pytunia.assemble_string(source, name + '.j',
                                        line_numbers=line_numbers)
            self.assertEqual(str(cm.exception) + '\n', e_stderr)
    return test


for _name in case_names():
    setattr(AssembleTests, 'test_' + _name, _make_assemble_test(_name))
    setattr(AssembleStringTests, 'test_' + _name,
            _make_assemble_string_test(_name))


def _valid_cases():
    return [n for n in case_names() if read_expected(n)[3]]


class InterfaceTests(InCasesDirectory):
    def test_default_source_name(self):
        # without a name, the SourceFile attribute is "<class>.j", so the
        # result equals that of a file named after the class
        checked = 0
        for name in _valid_cases():
            source = read_source(name)
            class_name, data = pytunia.assemble_string(
                source, line_numbers=options(name)[0])
            if '.source' not in source and \
                    class_name.split('/')[-1] == name:
                self.assertTrue(data == read_expected(name)[3][
                    class_name + '.class'], name)
                checked += 1
        self.assertGreater(checked, 10)

    def test_threads(self):
        cases = _valid_cases() * 3
        expected = dict((n, read_expected(n)[3]) for n in cases)

        def work(name):
            class_name, data = pytunia.assemble_string(
                read_source(name), name + '.j',
                line_numbers=options(name)[0])
            return expected[name][class_name + '.class'] == data

        with concurrent.futures.ThreadPoolExecutor(8) as pool:
            self.assertTrue(all(pool.map(work, cases)))

    def test_default_output_dir(self):
        # without output_dir the class file goes to the current directory
        tmp = tempfile.mkdtemp()
        old = os.getcwd()
        try:
            os.chdir(tmp)
            with open('Count.j', 'w') as f:
                f.write('.class public demo.pkg.Count\n'
                        '.super java/lang/Object\n')
            path = pytunia.assemble('Count.j')
            self.assertEqual(str(path), os.path.join('demo', 'pkg',
                                                     'Count.class'))
            self.assertTrue(os.path.isfile(path))
        finally:
            os.chdir(old)
            shutil.rmtree(tmp)

    def test_file_not_found(self):
        self.assertRaises(FileNotFoundError, pytunia.assemble,
                          'does-not-exist.j')

    def test_unknown_encoding(self):
        self.assertRaises(LookupError, pytunia.assemble, 'Fields.j',
                          tempfile.gettempdir(), encoding='no-such-codec')

    def test_diagnostics(self):
        source = ('.class public X\n.super java/lang/Object\n'
                  '.method public static m()V\n'
                  '  bipush 300 ; too big\n  return\n.end method\n')
        with self.assertRaises(pytunia.AssemblyError) as cm:
            pytunia.assemble_string(source, 'X.j')
        e = cm.exception
        self.assertEqual(e.filename, 'X.j')
        self.assertEqual(len(e.errors), 1)
        d = e.errors[0]
        self.assertEqual((d.filename, d.line, d.message),
                         ('X.j', 4, 'JAS Error: bipush value exceed size '
                                    'of byte'))
        # Jasmin shows the line up to the position after the number
        self.assertEqual(d.source_line, '  bipush 300 ')
        self.assertEqual(d.column, 13)
        # (this is exactly what jasmin.jar prints)
        self.assertEqual(str(e), 'X.j:4: JAS Error: bipush value exceed '
                                 'size of byte.\n  bipush 300 \n'
                                 '             ^\nX.j: Found 1 errors')
        # the exception can be pickled (e.g. for multiprocessing)
        e2 = pickle.loads(pickle.dumps(e))
        self.assertEqual(str(e2), str(e))

    def test_silent(self):
        # the library functions print nothing
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            pytunia.assemble_string('.class A\n.super java/lang/Object\n')
            try:
                pytunia.assemble_string('.class A\n')
            except pytunia.AssemblyError:
                pass
        self.assertEqual((out.getvalue(), err.getvalue()), ('', ''))

    def test_string_class_name(self):
        name, data = pytunia.assemble_string(
            '.class public a.b.C\n.super java/lang/Object\n')
        self.assertEqual(name, 'a/b/C')
        self.assertEqual(data[:4], b'\xca\xfe\xba\xbe')


if __name__ == '__main__':
    unittest.main()
