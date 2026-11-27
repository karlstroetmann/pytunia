"""
The command line interface of Jasmin (port of jasmin.Main).

usage: python3 -m pytunia [-d <outpath>] [-g] [-e <encoding>] <file> ...
"""

import codecs
import glob
import os
import sys

from .classfile import ClassFile
from .jas import JasError
from .javacompat import JavaException, printable
from .scanner import split_class_field, convert_chars

VERSION = "v2.4"

HELP1 = ("usage: jasmin [-d <outpath>] [-g] [-e <encoding>] <file> "
         "[<file> ...]\n")
HELP2 = ("           where   -g - autogenerate linenumbers\n"
         "                   -e - codepage for inputfile encoding\n"
         "                   -d - path for generated classfiles\n"
         "                file  - sourcefile (wildcards are allowed)\n")
HELP3 = ("   or: jasmin -version\n"
         "   or: jasmin -help")


class _FileNotFound(Exception):
    """corresponds to java.io.FileNotFoundException"""


def _print(stream, text):
    stream.write(printable(text) + "\n")
    stream.flush()


# --- java.io.File path handling ---------------------------------------------

def _normalize(path):
    """java.io.File's path normalization (Unix): remove duplicate and
    trailing slashes."""
    if os.sep != '/':
        return os.path.normpath(path) if path else path
    out = []
    prev = ''
    for c in path:
        if c == '/' and prev == '/':
            continue
        out.append(c)
        prev = c
    p = ''.join(out)
    if len(p) > 1 and p.endswith('/'):
        p = p[:-1]
    return p


def _resolve(parent, child):
    if os.sep != '/':
        return os.path.join(parent, child)
    if child == "":
        return parent
    if child.startswith('/'):
        if parent == '/':
            return child
        return parent + child
    if parent == '/':
        return parent + child
    return parent + '/' + child


def java_file(parent, child):
    """the path of new java.io.File(parent, child)"""
    if parent is None:
        return _normalize(child)
    if parent == "":
        return _resolve(os.sep, _normalize(child))
    return _resolve(_normalize(parent), _normalize(child))


def _os_path(path):
    # Java strings may contain lone surrogates, which the OS cannot take
    return printable(path)


def class_file_location(class_name, dest_path):
    """Determines where the class file of the class ``class_name`` (in
    internal form, e.g. "java/lang/Object") is placed: below ``dest_path``
    (None: the current directory), in subdirectories for its package.
    Returns the triple (simple class name, directory or None, path)."""
    package, simple_name = split_class_field(class_name)
    dest_dir = dest_path
    if package is not None:
        class_dir = convert_chars(package, "./", os.sep)
        if dest_dir is not None:
            dest_dir = dest_dir + os.sep + class_dir
        else:
            dest_dir = class_dir
    out_file = java_file(dest_dir, simple_name + ".class")
    return simple_name, dest_dir, out_file


# --- the driver -------------------------------------------------------------

class Main(object):
    def __init__(self, out=None, err=None):
        self.dest_path = None           # path for generated files
        self.encoding = None            # codepage of the input files
        self.generate_linenum = False   # autogenerate line numbers
        self.out = out if out is not None else sys.stdout
        self.err = err if err is not None else sys.stderr

    def _read_source(self, fname):
        try:
            with open(fname, 'rb') as f:
                data = f.read()
        except (OSError, ValueError):
            raise _FileNotFound()
        encoding = self.encoding if self.encoding is not None else 'utf-8'
        try:
            codecs.lookup(encoding)
        except LookupError:
            raise JavaException("java.io.UnsupportedEncodingException",
                                encoding)
        return data.decode(encoding, 'replace')

    def assemble(self, fname):
        """Assembles a single file.  Returns True if a class file has been
        generated."""
        out_file = None
        outp = None
        class_file = ClassFile(self.err)
        iocause = fname + ": file not found"

        try:
            text = self._read_source(fname)
            class_file.read_jasmin(text, os.path.basename(fname),
                                   self.generate_linenum)

            # if we got some errors, don't output a file - just return
            if class_file.error_count() > 0:
                _print(self.err, "%s: Found %d errors"
                       % (fname, class_file.error_count()))
                return False

            # determine where to place this class file
            class_name, dest_dir, out_file = class_file_location(
                class_file.get_class_name(), self.dest_path)
            iocause = class_name + ".class: file can't be created"
            if dest_dir is not None:
                # check that dest_dir exists
                dest = _os_path(java_file(None, dest_dir))
                if not os.path.exists(dest):
                    try:
                        os.makedirs(dest)
                    except OSError:
                        pass
                if not os.path.isdir(dest):
                    raise JavaException("java.io.IOException",
                                        "Cannot create directory")

            try:
                outp = open(_os_path(out_file), 'wb')
            except (OSError, ValueError):
                raise _FileNotFound()
            class_file.write(outp)
            outp.close()
            outp = None     # as marker
            _print(self.out, "Generated: " + out_file)

        except _FileNotFound:
            _print(self.err, iocause)
            sys.exit(-1)
        except JasError as e:
            class_file.report_error("JAS Error: " + e.get_message(),
                                    e.num_tag)
        except JavaException as e:
            class_file.report_error("%s: exception - <%s> %s."
                                    % (fname, e.java_class, e.get_message()))
        except RecursionError:
            class_file.report_error("%s: exception - <java.lang."
                                    "StackOverflowError> null." % fname)
        except Exception as e:      # an error of this port
            class_file.report_error("%s: exception - <%s> %s."
                                    % (fname, type(e).__name__, e))

        if class_file.error_count() > 0:
            _print(self.err, "%s: Found %d errors"
                   % (fname, class_file.error_count()))
            if outp is not None:
                try:
                    outp.close()
                    os.remove(_os_path(out_file))
                except Exception:
                    pass
            return False
        return True

    def _unarg_option(self, opt):
        _print(self.err, "Invaid command line: option " + opt +
               " required argument")
        sys.exit(-1)

    def _duplicate_option(self, opt):
        _print(self.err, "Duplicate option " + opt + " ignored")

    def run(self, args):
        """Processes the command line arguments (without the program
        name).  Returns the number of files that could not be
        assembled."""
        files = []
        if not args:
            _print(self.err, HELP1 + HELP3)
            sys.exit(-1)

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-help" or arg == "-?":
                _print(self.err, HELP1 + HELP2 + HELP3)
                sys.exit(0)
            if arg == "-version":
                _print(self.out, "Jasmin version: " + VERSION)
                sys.exit(0)
            if arg == "-g":
                self.generate_linenum = True
            elif arg == "-d":
                i += 1
                if i >= len(args):
                    self._unarg_option("-d")
                if self.dest_path is not None:
                    self._duplicate_option("-d")
                else:
                    self.dest_path = args[i]
            elif arg == "-e":
                i += 1
                if i >= len(args):
                    self._unarg_option("-e")
                if self.encoding is not None:
                    self._duplicate_option("-e")
                else:
                    self.encoding = args[i]
            else:
                files.append(arg)
            i += 1

        if os.name == 'nt':
            # the Java launcher expands wildcards on Windows
            expanded = []
            for f in files:
                magic = any(c in f for c in '*?[')
                matches = sorted(glob.glob(f)) if magic else []
                expanded.extend(matches or [f])
            files = expanded

        failed = 0
        for f in files:
            if not self.assemble(f):
                failed += 1
        return failed


def main(argv=None):
    """Entry point.  Like the Java version, the exit status is 0 even if
    some files contained errors."""
    if argv is None:
        argv = sys.argv[1:]
    Main().run(argv)
    return 0


if __name__ == '__main__':
    sys.exit(main())
