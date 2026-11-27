# pytunia

**Jasmin, the assembler for the Java Virtual Machine, in Python.**

pytunia is a Python port of [Jasmin 2.4](https://jasmin.sourceforge.net/).
It translates assembly code for the Java Virtual Machine (`.j` files) into
Java class files, and it produces **byte-for-byte the same class files** as
the original `jasmin.jar`. There are two extensions: class names can be
written with dots, e.g. `java.lang.Object` instead of `java/lang/Object`
(see [Dots in class names](#dots-in-class-names)), and types can be written
as in Java, e.g. `main(java.lang.String[]) void` instead of
`main([Ljava/lang/String;)V` (see
[Types in Java notation](#types-in-java-notation)).

pytunia is a library written in pure Python. It needs Python 3.12 or newer
and the parser generator [Larkita](https://github.com/karlstroetmann/Larkita),
which is installed with it.

## Installation

```
pip install pytunia
```

The latest development version can be installed from GitHub:

```
pip install git+https://github.com/karlstroetmann/pytunia
```

## Example

`HelloWorld.j`:

```
.class public HelloWorld
.super java/lang/Object

.method public static main([Ljava/lang/String;)V
    .limit stack 2
    getstatic java/lang/System/out Ljava/io/PrintStream;
    ldc "Hello, World!"
    invokevirtual java/io/PrintStream/println(Ljava/lang/String;)V
    return
.end method
```

With dots in the class names and the types in Java notation, the same
program reads:

```
.class public HelloWorld
.super java.lang.Object

.method public static main(java.lang.String[]) void
    .limit stack 2
    getstatic java.lang.System.out java.io.PrintStream
    ldc "Hello, World!"
    invokevirtual java.io.PrintStream.println(java.lang.String) void
    return
.end method
```

```python
import pytunia

pytunia.assemble("HelloWorld.j")    # writes HelloWorld.class
```

```
$ java HelloWorld
Hello, World!
```

## Usage

```python
import pytunia

# assemble a file and write the class file; returns its path
path = pytunia.assemble("Count.j")                       # examples/Count.class
path = pytunia.assemble("Count.j", output_dir="build")   # build/examples/Count.class

# assemble source text in memory; nothing is written to disk
class_name, data = pytunia.assemble_string(source)       # ("examples/Count", b"\xca\xfe...")
```

(Here `Count.j` defines the class `examples.Count`.)

`assemble(source_file, output_dir=None, *, line_numbers=False, encoding="utf-8")`

* Places the class file below `output_dir` (default: the current directory)
  in subdirectories for its package, as Jasmin does. `output_dir` can
  therefore be used directly as a class path:
  `java -cp build examples.Count`. Missing directories are created.
* `line_numbers=True` generates a line number table that refers to the lines
  of the assembly source (option `-g` of Jasmin), so that Java stack traces
  show the line numbers of the `.j` file.
* Returns the path of the class file as a `pathlib.Path`.

`assemble_string(source, name=None, *, line_numbers=False)`

* Returns the class name (in the internal form of the JVM, e.g.
  `"examples/Count"`) and the class file as `bytes`.
* `name` is the file name used in error messages and for the class file's
  `SourceFile` attribute. Without it, error messages show `<string>` and
  the attribute is `<class name>.j`.

### Errors

If the source contains errors, both functions raise `pytunia.AssemblyError`.
Its attribute `errors` is a list of `pytunia.Diagnostic` objects, each with
`filename`, `line`, `message`, `source_line` and `column`. `str(error)` is
the error output of the command line:

```python
try:
    pytunia.assemble("Bad.j")
except pytunia.AssemblyError as e:
    print(e)
```

```
Bad.j:4: Syntax error: unexpected name 'x', expected end of line or integer.
  iinc 1 x
         ^
Bad.j: Found 1 errors
```

Errors that are found while the class is built refer to the statement, so
they show no caret (`column` is `None`):

```
Bad.j:4: JAS Error: bipush value exceed size of byte.
  bipush 300
Bad.j: Found 1 errors
```

pytunia stops at the first syntax error. The error messages are pytunia's
own; they are not the same as those of `jasmin.jar`.

A file that cannot be read or written raises the usual `OSError`, for
example `FileNotFoundError`. The functions print nothing, and they can be
called from several threads at once.

### Command line

For debugging, the command line of the Java version is available. It is not
installed as a command:

```
python3 -m pytunia [-d <outpath>] [-g] [-e <encoding>] <file> [<file> ...]
```

### Low-level interface

`pytunia.ClassFile` has the methods of the Java class `jasmin.ClassFile`
(`read_jasmin`, `error_count`, `get_class_name`, `write`). Errors are
collected in its list `diagnostics`.

### Syntax highlighting

pytunia registers a lexer `pytunia` for [Pygments](https://pygments.org). It
extends the lexer of Jasmin that comes with Pygments by the
[types in Java notation](#types-in-java-notation): the name of a type is
coloured as a type, and the brackets `[]` of an array type and the commas
between parameters as punctuation. Sources written with descriptors are
coloured as by the lexer of Jasmin. The lexer needs Pygments, e.g.
`pip install pytunia[pygments]`:

```
pygmentize -l pytunia Hello.j
```

In Jupyter, `IPython.display.Code(filename='Hello.j', language='pytunia')`
displays an assembler file with syntax highlighting.

## Compatibility with Jasmin

### Why the output is identical

These details of the Java version had to be reproduced exactly:

* **Parsing.** The grammar in `pytunia/jasmin.g` describes the same language
  as Jasmin's grammar (`parser.cup`), and pytunia's scanner splits the source
  into tokens as Jasmin's scanner does. A source file that Jasmin accepts is
  accepted by pytunia, and vice versa, except for method signatures in Java
  notation, which only pytunia accepts (see
  [Types in Java notation](#types-in-java-notation)). The methods that
  build the class are called in the same order and with the same arguments
  as by the actions of Jasmin's parser.
* **Constant pool order.** Jasmin stores constant pool entries in a
  `java.util.Hashtable` keyed by strings and writes them in the table's
  enumeration order. pytunia reproduces this order (`String.hashCode`, bucket
  layout, rehashing).
* **Number formatting.** Some of these keys contain numbers formatted with
  `Float.toString` and `Double.toString`. These are not always the shortest
  representation, so the JDK 8 algorithm (`sun.misc.FloatingDecimal`) is
  ported as well.
* **Java strings and number types.** Strings are handled as UTF-16 code
  units, and constants are written in modified UTF-8. Numbers keep their
  Java type (Integer, Long, Float, Double), since Jasmin's behaviour depends
  on it. Number parsing follows Java's rules.

Quirks of Jasmin 2.4 are kept on purpose, because changing them would
change the output. For example:

* `iinc` gets a `wide` prefix unless the increment is exactly 127 (a typo in
  Jasmin's `jas.IincOperand`).
* `ldc2_w 0.1` stores the *float* value 0.1f as a double. Write `0.1d` to
  get the exact double.

### Dots in class names

The Java Virtual Machine writes class names with slashes (`java/lang/Object`),
and so do Jasmin's examples. pytunia also accepts the names that Java uses,
with dots (`java.lang.Object`), everywhere: in directives (`.class`,
`.super`, `.field`, `.var`, `.stack`, ...), in the operands of instructions
(`new java.lang.StringBuilder`,
`getstatic java.lang.System.out Ljava.io.PrintStream;`), and in descriptors
(`([Ljava.lang.String;)V`). The dots are converted to slashes, so both forms
give the same class file. The separator between a class and a member of it
can also be a dot or a slash: `java.lang.Object.<init>()V` and
`java/lang/Object/<init>()V` are the same method.

Generic signatures (`.signature "..."`) are not converted, because a dot
separates the name of an inner class there, e.g. `Lpkg/Outer<TT;>.Inner;`.
Strings are of course not converted either.

Jasmin 2.4 converts the dots only in some places: in `.class`, `.super`,
`.implements`, `.throws`, `.catch`, `.inner` and `.annotation`, in the
signatures of methods, and in the method and field references of
instructions, but not in the descriptor of a field reference. Everywhere
else, e.g. in `new`, `checkcast`, `ldc` of a class, and in the descriptors
of `.field` and `.var`, it copies the dots into the class file, which is
then invalid. Only for these sources does pytunia produce a different class
file than Jasmin.

### Types in Java notation

Types can also be written as in Java, with fully qualified class names,
instead of the descriptors of the JVM:

| Java notation | descriptor |
|---|---|
| `int`, `boolean`, `long[]` | `I`, `Z`, `[J` |
| `java.lang.String` | `Ljava/lang/String;` |
| `java.lang.String[][]` | `[[Ljava/lang/String;` |
| `main(java.lang.String[]) void` | `main([Ljava/lang/String;)V` |
| `max(int, int) int` | `max(II)I` |

The parameters of a method are separated by commas, and the return type
follows the closing parenthesis; blanks are allowed, but the signature must
be written on one line. The Java notation can be used

* in the signatures of `.method` and `.enclosing method`,
* in the method references of the `invoke...` instructions, e.g.
  `invokevirtual java.io.PrintStream.println(java.lang.String) void` and
  `invokeinterface java.util.List.size() int 1`,
* for the types of fields and local variables, e.g.
  `getstatic java.lang.System.out java.io.PrintStream` and in `.field` and
  `.var`,
* for array types in the operands of `checkcast`, `instanceof`,
  `anewarray`, `multianewarray` and `ldc`, and in `.stack` frames, e.g.
  `checkcast int[]` and `multianewarray int[][] 2`.

Annotations and generic signatures (`.signature`) keep the notation of the
JVM.

Both notations can be mixed. A word that is a valid descriptor keeps its
meaning, so every Jasmin source is translated as before. This matters only
for classes in the default package:

* `I` is the type `int`. A class whose name is one of the letters `B`, `C`,
  `D`, `F`, `I`, `J`, `S` and `Z` must be written as a descriptor, e.g.
  `LI;`.
* A parameter list without commas is read as a list of descriptors if it is
  one: `(IJ)` has the parameters `int` and `long`. A single parameter whose
  class name consists of these letters only, e.g. a class `ID`, must be
  written as a descriptor: `(LID;)`.

As in the JVM, the name of an inner class contains a `$`:
`java.util.Map$Entry`, not `java.util.Map.Entry`. Generic types
(`java.util.List<java.lang.String>`) and variable arguments
(`java.lang.String...`) are not supported.

Jasmin does not know this notation. It rejects signatures with blanks, and
it copies the other types unchanged into the class file, which is then
invalid.

### Known differences

* Class names with dots are converted to slashes in more places than in
  Jasmin (see [Dots in class names](#dots-in-class-names)).
* Types can be written in Java notation (see
  [Types in Java notation](#types-in-java-notation)). So pytunia accepts
  some sources that Jasmin rejects.
* The error messages are different (see [Errors](#errors)). pytunia
  reports at most one syntax error, while Jasmin tries to continue after a
  syntax error.
* Variable substitution with `.set name value` / `$name` is rejected with an
  error message. (Jasmin 2.4 takes the substituted token as `.method`, so it
  does not work there either.) Without `.set name`, `$name` is an ordinary
  name, as in Jasmin.
* The default source encoding is always UTF-8. Java up to version 17 uses
  the platform encoding instead.
* Java keeps some state of the assembler in static fields. pytunia keeps it
  in the objects of a single assembly instead, so assemblies can run in
  parallel.

## Development

### How the code is organized

The structure follows the Java sources of Jasmin. Class names are kept, and
method names are converted to snake_case.

| Python module | Java original |
|---|---|
| `pytunia/api.py`, `pytunia/diagnostics.py` | the library interface (`assemble`, `assemble_string`, `AssemblyError`); new in pytunia |
| `pytunia/main.py` | `jasmin.Main`: command line handling |
| `pytunia/classfile.py` | `jasmin.ClassFile`: builds the class |
| `pytunia/scanner.py` | `jasmin.Scanner`, `ScannerUtils` |
| `pytunia/jasmin.g` | the grammar (`jasmin/parser.cup`), written for Larkita; its string literals are the reserved words (`jasmin.ReservedWords`) |
| `pytunia/parser.py` | builds the parser from `jasmin.g` with Larkita and feeds it the tokens of the scanner |
| `pytunia/translator.py` | the semantic actions of `parser.cup`: walks the abstract syntax tree and calls the methods of `ClassFile` |
| `pytunia/insninfo.py` | `jasmin.InsnInfo`: instruction table |
| `pytunia/jas/` | the `jas` package that writes class files (constant pool, instructions, Code attribute, annotations, StackMap frames, ...) |
| `pytunia/javacompat.py` | emulation of the Java library behaviour that the output depends on |
| `pytunia/pygments_lexer.py` | the lexer for Pygments (see [Syntax highlighting](#syntax-highlighting)); new in pytunia |

### How a source file is assembled

1. `pytunia.scanner.Scanner` splits the source into tokens (`larkita.Token`
   objects). Reserved words get the terminals of their string literals in
   the grammar; the other tokens are `EOL`, `WORD`, `INSN`, `STR`, `INT`,
   `NUM` and `RELATIVE` (see the comment at the top of `jasmin.g`).
2. `pytunia.parser.join_signatures` joins the words of method signatures in
   Java notation that the scanner has split at blanks, e.g. `max(int,`,
   `int)` and `int` become `max(int, int) int`.
3. `pytunia.parser.parse` parses the tokens with the canonical LR(1) parser
   that Larkita generates from `jasmin.g` when pytunia is imported. The
   result is an abstract syntax tree made of nested tuples, e.g.
   `(".super", ("WORD", "java/lang/Object"), ("EOL", 2))`; an `EOL` token
   holds the line where its statement started.
4. `pytunia.translator.Translator` walks the tree with `match` statements and
   calls the methods of `ClassFile` (`set_class`, `new_method`, `plant`, ...).
   Types in Java notation are translated into descriptors by the functions
   in `pytunia/javatypes.py`.
5. `ClassFile.to_bytes` writes the class file with the `jas` package.

To change the syntax, edit `jasmin.g` and the matching case in
`translator.py`. To see the automaton that Larkita builds, including any
conflicts, run

```
python3 -c "from larkita import Larkita; Larkita.open('pytunia/jasmin.g', lexer='basic')"
```

which writes `pytunia/jasmin.out` (ignored by git).

### Tests

```
pip install -e .        # installs Larkita
python3 -m unittest discover -s tests
```

`tests/cases/` contains about 90 Jasmin files. They cover every instruction
form, all directives (fields with constant values, annotations, stack maps,
inner classes, debug information, ...), character encodings, and many kinds
of errors. `tests/expected/` holds the results of `jasmin.jar` for each case:
class files, standard output, standard error and exit status.

* `tests/test_api.py` assembles every case with `assemble()` and
  `assemble_string()`. The class files must be identical to those of the
  Java version. For sources with errors, `AssemblyError` must be raised, and
  its first error must refer to the line given in
  `tests/expected_errors.py`.
* `tests/test_dots.py` checks the extension
  [Dots in class names](#dots-in-class-names): a source that uses every
  kind of class name and descriptor must give the same class file when all
  its slashes are written as dots.
* `tests/test_java_types.py` checks the extension
  [Types in Java notation](#types-in-java-notation): a class written in
  Java notation must give the same class file as the same class written with
  descriptors.
* `tests/test_pygments_lexer.py` checks the lexer for Pygments: every case
  must be coloured as by the lexer of Jasmin, and the types in Java notation
  must be coloured as types. It is skipped if Pygments is not installed.
* `tests/test_cli.py` runs the command line (`python3 -m pytunia`) on every
  case and compares the class files, standard output and exit status with
  those of the Java version, and standard error for the cases without
  errors. It also checks the number formatting against Java for about
  10,000 values.

Running the tests needs neither Java nor Jasmin.

### Comparing with the Java version

The following tools need the original Jasmin 2.4 (`jasmin-2.4.zip` from the
[Jasmin project on SourceForge](https://sourceforge.net/projects/jasmin/)).
By default they look for it in a directory `jasmin-2.4` next to the
repository.

To regenerate the expected test results (needs `java` and `javac`):

```
python3 tests/make_expected.py ../jasmin-2.4/jasmin.jar
```

`tools/fuzz_compare.py` runs randomly mutated Jasmin files through both
versions and reports any file where the class files, the standard output,
the exit status or the presence of errors differ. Differences caused by the
extensions are expected: a mutation can put a dot into a class name or a
type in Java notation (e.g. `int`) where Jasmin expects a descriptor (see
[Dots in class names](#dots-in-class-names) and
[Types in Java notation](#types-in-java-notation)).

```
python3 tools/fuzz_compare.py --jar ../jasmin-2.4/jasmin.jar -n 20 tests/cases/*.j
```

## License

Jasmin is distributed under a BSD-style license, and pytunia keeps it; see
[LICENSE.txt](https://github.com/karlstroetmann/pytunia/blob/main/LICENSE.txt), which also lists the credits.
