"""
The library interface of the assembler.

    import pytunia

    # assemble a file and write the class file (returns its path)
    path = pytunia.assemble("Hello.j", output_dir="classes")

    # assemble source text in memory
    class_name, data = pytunia.assemble_string(source)

Both functions raise pytunia.AssemblyError if the source contains errors.
They print nothing, and they can be called from several threads at once.
"""

import os
import pathlib

from .classfile import ClassFile
from .diagnostics import AssemblyError
from .jas import JasError
from .javacompat import JavaException, from_java_string
from .main import class_file_location, _os_path
from .scanner import split_class_field


def _assemble(text, filename, display_name, line_numbers,
              default_source=False):
    """Assembles source text; returns the ClassFile object and the class
    file.  ``filename`` is used in the error messages and as the default
    for the SourceFile attribute; ``display_name`` is used where Jasmin
    shows the name given on the command line."""
    cf = ClassFile()
    try:
        cf.read_jasmin(text, filename, line_numbers)
        if cf.error_count() == 0:
            if default_source and not cf.source_given:
                _, simple_name = split_class_field(cf.get_class_name())
                cf.source_name = simple_name + ".j"
            return cf, cf.to_bytes()
    except JasError as e:
        cf.report_error("JAS Error: " + e.get_message(), e.num_tag)
    except JavaException as e:
        cf.report_error("%s: exception - <%s> %s."
                        % (display_name, e.java_class, e.get_message()))
    raise AssemblyError(display_name, cf.diagnostics)


def assemble(source_file, output_dir=None, *, line_numbers=False,
             encoding="utf-8"):
    """Assembles the Jasmin file ``source_file`` and writes the class file.

    The class file is placed below ``output_dir`` (default: the current
    directory) in subdirectories for its package, e.g. the class
    ``examples.Count`` goes to ``<output_dir>/examples/Count.class``.  So
    ``output_dir`` can be used as a class path.  Directories are created
    as needed.

    If ``line_numbers`` is true, a line number table that refers to the
    lines of the Jasmin source is generated (option -g of Jasmin).
    ``encoding`` is the encoding of the source file.

    Returns the path of the class file (a pathlib.Path).  Raises
    AssemblyError if the source contains errors and OSError (e.g.
    FileNotFoundError) if a file cannot be read or written.

    Note: file names in ``.attribute`` directives are relative to the
    current directory, as in Jasmin.
    """
    fname = os.fsdecode(source_file)
    with open(fname, 'rb') as f:
        data = f.read()
    text = data.decode(encoding, 'replace')
    cf, code = _assemble(text, os.path.basename(fname), fname, line_numbers)
    dest_path = None if output_dir is None else os.fsdecode(output_dir)
    _, dest_dir, out_file = class_file_location(cf.get_class_name(),
                                                dest_path)
    if dest_dir is not None:
        os.makedirs(_os_path(dest_dir), exist_ok=True)
    path = pathlib.Path(_os_path(out_file))
    path.write_bytes(code)
    return path


def assemble_string(source, name=None, *, line_numbers=False):
    """Assembles Jasmin source text in memory.

    ``name`` is the name of the source file; it is used in error messages
    and as the default for the SourceFile attribute of the class.  If it
    is omitted, error messages show "<string>" and the SourceFile
    attribute is "<class name>.j" (unless the source has a .source
    directive), as if the source had been read from a file named after
    the class.

    Returns the pair (class name, class file).  The class name is in the
    internal form of the JVM, e.g. "examples/Count"; the class file is a
    bytes object.  Raises AssemblyError if the source contains errors.
    """
    if name is None:
        filename = display_name = "<string>"
    else:
        display_name = os.fsdecode(name)
        filename = os.path.basename(display_name)
    cf, code = _assemble(source, filename, display_name, line_numbers,
                         default_source=name is None)
    return from_java_string(cf.get_class_name()), code
