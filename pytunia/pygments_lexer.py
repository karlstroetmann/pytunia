"""
A lexer for Pygments that highlights the assembler code of pytunia.

pytunia registers this lexer as a Pygments plugin with the name 'pytunia',
so it can be used as in `pygmentize -l pytunia Hello.j` or, in Jupyter, as
in `display(Code(filename='Hello.j', language='pytunia'))`.  Pygments is not
a requirement of pytunia; this module is only imported when Pygments looks
for its lexers.

The lexer extends the lexer of Jasmin that comes with Pygments by the types
in Java notation (README, "Types in Java notation").  The lexer of Jasmin
only knows the descriptors of the JVM, e.g. "[Ljava/lang/String;".  It
colours the "[" of "java.lang.String[]" as punctuation, but the "]" as a
type, it counts the comma between two parameters as part of a type, and it
splits a class name at every capital "L".  Here, the name of a type is
coloured as a type and the brackets "[]" of an array type as punctuation, as
in the lexer of Java.  Sources that only use descriptors are coloured as by
the lexer of Jasmin.

The lecture notes "Formal Languages and Their Applications" use a copy of
this class with minted (pytunia_lexer.py), since the Pygments of TeX Live
cannot load plugins.  Keep the classes identical.
"""

from pygments.lexer import bygroups, inherit
from pygments.lexers.jvm import JasminLexer
from pygments.token import Keyword, Punctuation, Whitespace

# an identifier of Java, and a primitive type or a class name, whose parts
# are separated by "." or "/"
_IDENTIFIER = r'(?:[^\W\d]|\$)[\w$]*'
_TYPE_NAME = rf'{_IDENTIFIER}(?:[./]{_IDENTIFIER})*'

# a type in Java notation ends before a blank, a comma, a closing
# parenthesis, or the end of the line
_TYPE_END = r'(?=[\s,)]|$)'

# a type in Java notation, and an array type in Java notation
_JAVA_TYPE = (rf'({_TYPE_NAME})((?:\[\])*){_TYPE_END}',
              bygroups(Keyword.Type, Punctuation), '#pop')
_ARRAY_TYPE = (rf'({_TYPE_NAME})((?:\[\])+){_TYPE_END}',
               bygroups(Keyword.Type, Punctuation), '#pop')


class PytuniaLexer(JasminLexer):
    """The assembler code of pytunia: the syntax of Jasmin together with
    the types in Java notation."""
    name = 'Pytunia'
    url = 'https://github.com/karlstroetmann/pytunia'
    aliases = ['pytunia']
    filenames = ['*.j', '*.jas']

    tokens = {
        # the type of a parameter, of a return value, of a field, or of a
        # local variable
        'descriptor/convert-dots': [_JAVA_TYPE, inherit],
        'descriptor/no-dots': [_JAVA_TYPE, inherit],
        # the parameters of a method, which are separated by commas
        'descriptors/convert-dots': [(r'[ \t]+', Whitespace),
                                     (r',', Punctuation), inherit],
        # the operand of checkcast, instanceof, anewarray, and ldc, and a
        # class in a .stack frame
        'class/no-dots': [_ARRAY_TYPE, inherit],
    }
