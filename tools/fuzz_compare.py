#!/usr/bin/env python3
"""
Differential testing of the Python port against the original Jasmin.

Random mutations of the given Jasmin files (lines deleted, duplicated or
swapped, tokens replaced, characters inserted, ...) are assembled with
both versions, and the results are compared: the generated class files,
the standard output, the exit status, and which files contain errors.
(The error messages themselves differ.)  Files that produce different
results are saved for inspection.

usage: python3 fuzz_compare.py [-n ROUNDS] [-b BATCH] [-s SEED]
                               [--jar JASMIN_JAR] [--keep DIR] files...

Requires java on the PATH.
"""

import argparse
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_JAR = os.path.join(ROOT, os.pardir, 'jasmin-2.4', 'jasmin.jar')

EXTRA_TOKENS = [
    '.method', '.end', 'method', '.limit', 'stack', 'locals', '.field',
    '.class', '.super', '.var', 'is', 'from', 'to', '.catch', 'using',
    '.line', '.throws', '.annotation', 'visible', 'invisible', 'default',
    '.stack', 'offset', 'use', '.set', '.inner', '.signature', '.source',
    '.bytecode', '50.0', '49.0', 'public', 'static', 'final', 'abstract',
    'tableswitch', 'lookupswitch', ':', '=', '"', "'", '\\', '\\u0041',
    '$+3', '$-3', '$', '0', '1', '-1', '127', '128', '256', '65536',
    '2147483648', '1.5', '1.5d', '0x10', '-0x1.8p1', '1e5', 'L1', 'L1:',
    'iload', 'iinc', 'ldc', 'ldc2_w', 'goto', 'goto_w', 'invokevirtual',
    'invokeinterface', 'getstatic', 'newarray', 'multianewarray', 'int',
    'java/lang/Object', 'java/lang/Object/<init>()V', 'Ljava/lang/String;',
    'I', '[I', '@', 'e', 's', '"str"', '"\\n"', '"\\777"', ';', 'Integer',
    'Object', 'Uninitialized', 'Top', 'all', 'signature', '\t', '\r',
]


_CLASS_RE = re.compile(r'^(\.(?:class|interface)[ \t]+(?:[a-z]+[ \t]+)*)'
                       r'([^\s]+)', re.M)


def mutate(text, rnd):
    lines = text.split('\n')
    for _ in range(rnd.randint(1, 3)):
        if not lines:
            lines = ['']
        kind = rnd.randrange(8)
        i = rnd.randrange(len(lines))
        if kind == 0:                                   # delete a line
            del lines[i]
        elif kind == 1:                                 # duplicate a line
            lines.insert(i, lines[i])
        elif kind == 2:                                 # swap two lines
            j = rnd.randrange(len(lines))
            lines[i], lines[j] = lines[j], lines[i]
        elif kind in (3, 4):                            # replace a token
            toks = re.split(r'(\s+)', lines[i])
            words = [k for k, t in enumerate(toks) if t and not t.isspace()]
            tok = rnd.choice(EXTRA_TOKENS)
            if words:
                toks[rnd.choice(words)] = tok
                lines[i] = ''.join(toks)
            else:
                lines[i] = '  ' + tok
        elif kind == 5:                                 # insert a token
            toks = lines[i].split(' ')
            toks.insert(rnd.randint(0, len(toks)), rnd.choice(EXTRA_TOKENS))
            lines[i] = ' '.join(toks)
        elif kind == 6:                                 # delete characters
            if lines[i]:
                a = rnd.randrange(len(lines[i]))
                b = min(len(lines[i]), a + rnd.randint(1, 4))
                lines[i] = lines[i][:a] + lines[i][b:]
        else:                                           # insert a char
            c = rnd.choice(' \t:=";\'\\$.-+0123456789abcLx()/[')
            a = rnd.randint(0, len(lines[i]))
            lines[i] = lines[i][:a] + c + lines[i][a:]
    if rnd.random() < 0.1:
        return '\n'.join(lines).rstrip('\n')            # no final newline
    return '\n'.join(lines)


_FOUND_RE = re.compile(r'^(.*): Found \d+ errors$', re.M)


def run(command, files, workdir, outdir):
    """Assembles the files; returns the standard output, the exit status,
    the class files and the names of the files with errors."""
    proc = subprocess.run(command + ['-d', outdir] + files, cwd=workdir,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    classes = {}
    for root, _, fns in os.walk(outdir):
        for fn in fns:
            path = os.path.join(root, fn)
            with open(path, 'rb') as f:
                classes[os.path.relpath(path, outdir)] = f.read()
    out = proc.stdout.decode('utf-8', 'replace').replace(outdir, '<OUT>')
    err = proc.stderr.decode('utf-8', 'replace')
    failed = sorted(_FOUND_RE.findall(err))
    return out, proc.returncode, classes, failed


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[1])
    ap.add_argument('-n', type=int, default=20, help='number of rounds')
    ap.add_argument('-b', type=int, default=25, help='files per round')
    ap.add_argument('-s', type=int, default=1, help='random seed')
    ap.add_argument('--jar', default=DEFAULT_JAR)
    ap.add_argument('--keep', default='fuzz-failures',
                    help='directory for files with different results')
    ap.add_argument('files', nargs='+')
    args = ap.parse_args()

    corpus = []
    for fn in args.files:
        with open(fn, 'rb') as f:
            corpus.append(f.read().decode('utf-8', 'replace'))
    java = ['java', '-Dfile.encoding=UTF-8', '-jar',
            os.path.abspath(args.jar)]
    python = [sys.executable, '-m', 'pytunia']
    os.environ['PYTHONPATH'] = ROOT + os.pathsep + os.environ.get(
        'PYTHONPATH', '')
    rnd = random.Random(args.s)
    failures = 0
    for rnd_no in range(args.n):
        work = tempfile.mkdtemp()
        try:
            names = []
            for k in range(args.b):
                name = 'F%03d.j' % k
                # give every file its own class name, so that the class
                # files of a batch do not overwrite each other
                text = _CLASS_RE.sub(r'\1\2_F%03d' % k, rnd.choice(corpus),
                                     count=1)
                with open(os.path.join(work, name), 'w', encoding='utf-8',
                          newline='') as f:
                    f.write(mutate(text, rnd))
                names.append(name)
            jout, pout = tempfile.mkdtemp(), tempfile.mkdtemp()
            try:
                # assemble all files of a round in one batch (much faster);
                # only if the results differ, compare file by file
                rj = run(java, names, work, jout)
                rp = run(python, names, work, pout)
            finally:
                shutil.rmtree(jout)
                shutil.rmtree(pout)
            if rj == rp:
                print('round %d: %d files ok, %d class files'
                      % (rnd_no, len(names), len(rj[2])))
                continue
            for name in names:
                jout, pout = tempfile.mkdtemp(), tempfile.mkdtemp()
                try:
                    rj = run(java, [name], work, jout)
                    rp = run(python, [name], work, pout)
                finally:
                    shutil.rmtree(jout)
                    shutil.rmtree(pout)
                if rj != rp:
                    failures += 1
                    os.makedirs(args.keep, exist_ok=True)
                    keep = os.path.join(args.keep, 'r%d_%s' % (rnd_no, name))
                    shutil.copy(os.path.join(work, name), keep)
                    print('round %d: %s DIFFERS (saved as %s)'
                          % (rnd_no, name, keep))
                    if rj[0] != rp[0]:
                        print('  java   stdout: %r' % rj[0][-300:])
                        print('  python stdout: %r' % rp[0][-300:])
                    if rj[1] != rp[1]:
                        print('  status: java %d, python %d' % (rj[1], rp[1]))
                    if rj[2] != rp[2]:
                        print('  class files differ')
                    if rj[3] != rp[3]:
                        print('  errors: java %s, python %s'
                              % ('yes' if rj[3] else 'no',
                                 'yes' if rp[3] else 'no'))
        finally:
            shutil.rmtree(work)
    print('%d difference(s)' % failures)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
