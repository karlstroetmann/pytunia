# pytunia

pytunia is a Python port of Jasmin 2.4, the assembler for the JVM. It turns
`.j` files into class files that are **byte-for-byte identical** to those of
the original `jasmin.jar`. That is the one hard requirement: every change must
keep the class files identical. Error messages do *not* have to match Jasmin's.

There are two deliberate exceptions. First (README, "Dots in class names"):
class names may be written with dots (`java.lang.Object`) everywhere, also in descriptors.
Jasmin converts the dots to slashes only in some places and copies them into
the class file elsewhere, which makes it invalid; pytunia converts them
everywhere except in generic signatures (`.signature`) and strings. So only
sources for which Jasmin writes invalid class files give different output.
The conversion happens with `convert_dots` where names enter: in
translator.py (like Jasmin's parser actions), in the `plant_*` methods of
classfile.py (operands of instructions) and in jas/annotation.py (`c`
values). `tests/test_dots.py` tests it.

Second (README, "Types in Java notation"): types may be written as in Java,
e.g. `main(java.lang.String[]) void` or `getstatic java.lang.System.out
java.io.PrintStream`. `parser.join_signatures` joins the words of a method
signature that the scanner split at blanks (only after `.method`,
`.enclosing method` and the invoke instructions); javatypes.py translates the
types into descriptors at the same places as `convert_dots` (but not in
annotations). A word that is a valid descriptor keeps its meaning, and a word
that is neither stays unchanged, so every source that Jasmin accepts gives
the same class file as before, unless Jasmin's is invalid. Jasmin rejects the
joined signatures, so this is the one place where pytunia accepts more than
Jasmin. `tests/test_java_types.py` tests it.

It needs Python 3.12+ and one dependency, the parser generator
[Larkita](https://github.com/karlstroetmann/Larkita) (by the same author as
pytunia).

## Layout

```
pytunia/
  __init__.py      public API: assemble, assemble_string, AssemblyError, Diagnostic, ClassFile
  api.py           assemble() / assemble_string(); turns errors into AssemblyError
  main.py          command line (python3 -m pytunia), port of jasmin.Main
  diagnostics.py   Diagnostic and AssemblyError
  jasmin.g         the grammar (Larkita syntax); string literals = reserved words
  parser.py        builds the Larkita parser from jasmin.g at import; parse(scanner);
                   join_signatures joins signatures in Java notation (new in pytunia)
  javatypes.py     types in Java notation -> descriptors (new in pytunia)
  scanner.py       hand-written tokenizer (port of jasmin.Scanner), yields larkita.Token
  translator.py    walks the AST and calls ClassFile (= the semantic actions of parser.cup)
  classfile.py     ClassFile: builds the class (port of jasmin.ClassFile), reports errors
  insninfo.py      instruction table (jasmin.InsnInfo)
  javacompat.py    Java behaviour the output depends on (Hashtable order, Float.toString, ...)
  jas/             port of Jasmin's jas package: constant pool, instructions, attributes
tests/
  cases/*.j        ~90 test sources; a line "; ARGS: -g" gives command line options
  expected/        results of jasmin.jar per case (generated, do not edit by hand)
  expected_errors.py  line of the first error for every case with errors
  test_api.py, test_cli.py, make_expected.py
  test_dots.py     the extension "Dots in class names" (no jasmin.jar results)
  test_java_types.py  the extension "Types in Java notation" (no jasmin.jar results)
tools/fuzz_compare.py   differential fuzzing against jasmin.jar
```

Class and method names follow the Java sources of Jasmin (methods in
snake_case), so the Java original stays easy to compare.

## How a file is assembled

1. `Scanner` (scanner.py) produces tokens. Reserved words get the terminal
   names that Larkita gives the literals of `jasmin.g` (`parser.KEYWORDS`).
   The other token types are `EOL WORD INSN STR INT NUM RELATIVE`. An `EOL`
   stands for one or more line breaks and comments; its value is the line
   where the current statement started.
2. `parser.parse` runs Larkita's canonical LR(1) parser on these tokens and
   returns the AST as nested tuples, following Larkita's rules: string literals
   form the head, named tokens become `(TYPE, value)`, `-> "name"` sets the
   head. `parse` uses `Larkita.parse_tokens` and `Larkita.literals`
   (new in Larkita 0.8). The parser is built with `out_file=False`, so it
   writes no `.out` report.
3. `Translator` (translator.py) pattern-matches the tuples and calls the
   `ClassFile` methods. Their **order and arguments must stay exactly as in
   Jasmin's parser.cup actions**: the constant pool order (and so the bytes)
   depends on it. `_line(node)` (the first `EOL` in a node) sets
   `ClassFile.line_num`, which feeds the `-g` line number tables and error
   messages.
4. `ClassFile.to_bytes()` writes the class with the `jas` package.

Syntax errors (`larkita.UnexpectedToken`) are reported at the token, and
parsing stops at the first one. Scanner errors (`JasError`) are reported at
the scanner position. Errors found while translating refer to the current
statement.

## Changing the grammar

Edit `jasmin.g` and the matching `case` in translator.py. The language must
stay the same as Jasmin's: anything Jasmin accepts must be accepted, and
anything it rejects must be rejected (except the method signatures in Java
notation, see above). To check for conflicts, run

    python3 -c "from larkita import Larkita; Larkita.open('pytunia/jasmin.g', lexer='basic')"

and read `pytunia/jasmin.out` (git ignores it).

## Tests

    pip install -e .                       # Python 3.12+, installs larkita
    python3 -m unittest discover -s tests

Valid cases compare class files, stdout and stderr with `tests/expected/`.
Error cases check that no class file is written, the shape of the report, and
the line in `expected_errors.py`. New error cases need an entry there.
Regenerating `tests/expected/` and running `tools/fuzz_compare.py` need
`jasmin.jar` (the original Jasmin 2.4, expected in `../jasmin-2.4/`). It is
not in the repository.

## Conventions

- Quirks of Jasmin 2.4 that affect the output are kept on purpose (README,
  "Compatibility with Jasmin"). Do not "fix" them.
- Java semantics live in javacompat.py: strings are UTF-16 code unit
  sequences, numbers keep their Java type (JavaInteger, JavaLong, ...).
- `ClassFile` keeps no global state, so assemblies can run in parallel
  threads.
- iCloud Drive may create conflict copies ("name 2.py"). They are
  git-ignored; don't commit them.
