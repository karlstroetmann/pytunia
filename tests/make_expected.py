#!/usr/bin/env python3
"""
Generate the expected results of the test cases with the original
(Java) Jasmin.

usage: python3 make_expected.py [path/to/jasmin.jar]

For every file cases/<name>.j the Java version of Jasmin is run (in the
directory cases, with the extra command line arguments given in a line
"; ARGS: ..." of the file) and its results are stored in expected/<name>:

    stdout.txt   standard output (the output directory is shown as <OUT>)
    stderr.txt   standard error
    status.txt   exit status
    classes/     the generated class files

In addition expected/numbers.txt is created; it contains the results of
Java's Float.toString and Double.toString for many values.  This needs
javac and java on the PATH.
"""

import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, 'cases')
EXPECTED = os.path.join(HERE, 'expected')
DEFAULT_JAR = os.path.join(HERE, os.pardir, os.pardir, 'jasmin-2.4',
                           'jasmin.jar')


def case_args(path):
    """the extra command line arguments of a test case"""
    with open(path, 'rb') as f:
        for line in f.read().decode('latin-1').splitlines()[:5]:
            if line.startswith('; ARGS:'):
                return line[len('; ARGS:'):].split()
    return []


def case_names():
    return sorted(f[:-2] for f in os.listdir(CASES) if f.endswith('.j'))


def run_case(command, name, outdir, env=None):
    """Runs an assembler (command is a list) on a test case.  Returns
    (stdout, stderr, status, {relative class path: bytes})."""
    args = command + ['-d', outdir] + case_args(
        os.path.join(CASES, name + '.j')) + [name + '.j']
    proc = subprocess.run(args, cwd=CASES, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=env)
    stdout = proc.stdout.decode('utf-8', 'replace').replace(outdir, '<OUT>')
    stderr = proc.stderr.decode('utf-8', 'replace').replace(outdir, '<OUT>')
    classes = {}
    for root, _, files in os.walk(outdir):
        for f in files:
            path = os.path.join(root, f)
            rel = os.path.relpath(path, outdir).replace(os.sep, '/')
            with open(path, 'rb') as fp:
                classes[rel] = fp.read()
    return stdout, stderr, proc.returncode, classes


NUMBERS_JAVA = r'''
import java.io.*;
public class Numbers {
    public static void main(String[] args) throws Exception {
        BufferedReader in =
            new BufferedReader(new InputStreamReader(System.in));
        String line;
        while ((line = in.readLine()) != null) {
            String[] p = line.split(" ");
            if (p[0].equals("F")) {
                float f = Float.intBitsToFloat((int)Long.parseLong(p[1], 16));
                System.out.println(line + " " + Float.toString(f));
            } else {
                long bits = new java.math.BigInteger(p[1], 16).longValue();
                double d = Double.longBitsToDouble(bits);
                System.out.println(line + " " + Double.toString(d));
            }
        }
    }
}
'''


def number_samples():
    rnd = random.Random(1234)
    out = []
    specials = [0.0, -0.0, 1.0, -1.0, 0.1, 0.5, 1.5, 3.14, 100.0, 1e7,
                9999999.0, 12345678.0, 0.001, 0.0009999, 1e-3, 1e-4,
                1e10, 1e38, 3.4028235e38, 1.4e-45, 1.17549435e-38, 2.5e-5,
                123456.789, 1e21, 1e22, 1e23, 2e23, 5e-324,
                1.7976931348623157e308,
                2.2250738585072014e-308, 4.35, 0.3, 2.0 / 3.0, 1 / 3.0]
    for v in specials:
        out.append('D %016x' % struct.unpack('>Q', struct.pack('>d', v))[0])
        try:
            out.append('F %08x' % struct.unpack('>I', struct.pack('>f', v))[0])
        except OverflowError:
            pass
    for _ in range(3000):
        out.append('D %016x' % rnd.getrandbits(63))
        out.append('F %08x' % rnd.getrandbits(31))
    for _ in range(2000):
        # "simple" decimal numbers, as they appear in source files
        digits = rnd.randint(1, 9)
        v = rnd.randint(1, 10 ** digits) * 10.0 ** rnd.randint(-12, 12)
        out.append('D %016x' % struct.unpack('>Q', struct.pack('>d', v))[0])
        try:
            out.append('F %08x' % struct.unpack('>I',
                                                struct.pack('>f', v))[0])
        except OverflowError:
            pass
    return out


def make_numbers(target):
    tmp = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmp, 'Numbers.java'), 'w') as f:
            f.write(NUMBERS_JAVA)
        subprocess.check_call(['javac', 'Numbers.java'], cwd=tmp)
        data = '\n'.join(number_samples()) + '\n'
        result = subprocess.run(['java', '-cp', tmp, 'Numbers'],
                                input=data.encode(), stdout=subprocess.PIPE,
                                check=True).stdout
        with open(os.path.join(target, 'numbers.txt'), 'wb') as f:
            f.write(result)
    finally:
        shutil.rmtree(tmp)


def sync_tree(src, dst):
    """Make the directory dst identical to src, touching only files that
    changed.  (Deleting and re-creating whole directories confuses file
    synchronization services like iCloud Drive.)"""
    os.makedirs(dst, exist_ok=True)
    wanted = set()
    for root, _, files in os.walk(src):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), src)
            wanted.add(rel)
            target = os.path.join(dst, rel)
            with open(os.path.join(src, rel), 'rb') as f:
                data = f.read()
            if os.path.exists(target):
                with open(target, 'rb') as f:
                    if f.read() == data:
                        continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(data)
    for root, dirs, files in os.walk(dst, topdown=False):
        for fn in files:
            path = os.path.join(root, fn)
            if os.path.relpath(path, dst) not in wanted:
                os.remove(path)
        for d in dirs:
            path = os.path.join(root, d)
            if not os.listdir(path):
                os.rmdir(path)


def main():
    jar = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_JAR)
    command = ['java', '-Dfile.encoding=UTF-8', '-jar', jar]
    work = tempfile.mkdtemp()
    try:
        for name in case_names():
            outdir = tempfile.mkdtemp()
            try:
                stdout, stderr, status, classes = run_case(command, name,
                                                           outdir)
            finally:
                shutil.rmtree(outdir)
            target = os.path.join(work, name)
            os.makedirs(target)
            with open(os.path.join(target, 'stdout.txt'), 'w') as f:
                f.write(stdout)
            with open(os.path.join(target, 'stderr.txt'), 'w') as f:
                f.write(stderr)
            with open(os.path.join(target, 'status.txt'), 'w') as f:
                f.write('%d\n' % status)
            for rel, data in classes.items():
                path = os.path.join(target, 'classes', rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'wb') as f:
                    f.write(data)
            print('%-24s status %d, %d class file(s)'
                  % (name, status, len(classes)))
        make_numbers(work)
        print('wrote numbers.txt')
        sync_tree(work, EXPECTED)
    finally:
        shutil.rmtree(work)


if __name__ == '__main__':
    main()
