"""
The tokenizer for Jasmin source files (port of jasmin.Scanner,
jasmin.ScannerUtils and jasmin.ReservedWords).

The scanner works on a Java string, i.e. a sequence of UTF-16 code
units (see javacompat.to_java_string).
"""

from . import sym
from . import insninfo
from .jas.errors import JasError
from .javacompat import (JavaException, JavaInteger, JavaLong, JavaFloat,
                         JavaDouble, parse_int, parse_long, parse_double,
                         java_digit, substring, char_at, to_float32)


# ---------------------------------------------------------------------------
# tokens
# ---------------------------------------------------------------------------

class Token(object):
    """A symbol of the parser.  ``sym`` is the symbol number,
    ``parse_state`` is the parser state when the symbol is on the parse
    stack and ``value`` is the semantic value (str_val, int_val, num_val
    or var_val in the Java version)."""

    __slots__ = ('sym', 'parse_state', 'value')

    def __init__(self, sym_num, value=None, parse_state=-1):
        self.sym = sym_num
        self.value = value
        self.parse_state = parse_state

    def __repr__(self):
        return 'Token(%s, %r)' % (sym.NAMES.get(self.sym, self.sym),
                                  self.value)


# ---------------------------------------------------------------------------
# reserved words
# ---------------------------------------------------------------------------

# the reserved words and their symbol numbers
RESERVED_WORDS = dict([
    # Jasmin directives
    (".annotation", sym.DANNOTATION),
    (".attribute", sym.DATTRIBUTE),
    (".bytecode", sym.DBYTECODE),
    (".catch", sym.DCATCH),
    (".class", sym.DCLASS),
    (".deprecated", sym.DDEPRECATED),
    (".end", sym.DEND),
    (".field", sym.DFIELD),
    (".implements", sym.DIMPLEMENTS),
    (".inner", sym.DINNER),
    (".interface", sym.DINTERFACE),
    (".limit", sym.DLIMIT),
    (".line", sym.DLINE),
    (".method", sym.DMETHOD),
    (".set", sym.DSET),
    (".source", sym.DSOURCE),
    (".super", sym.DSUPER),
    (".throws", sym.DTHROWS),
    (".var", sym.DVAR),
    (".debug", sym.DDEBUG),
    (".enclosing", sym.DENCLOSING),
    (".signature", sym.DSIGNATURE),
    (".stack", sym.DSTACK),

    # reserved words used in Jasmin directives
    ("field", sym.FIELD),
    ("from", sym.FROM),
    ("method", sym.METHOD),
    ("to", sym.TO),
    ("is", sym.IS),
    ("using", sym.USING),
    ("signature", sym.SIGNATURE),
    ("stack", sym.STACK),
    ("offset", sym.OFFSET),
    ("locals", sym.LOCALS),
    ("use", sym.USE),
    ("inner", sym.INNER),
    ("outer", sym.OUTER),
    ("class", sym.CLASS),
    ("visible", sym.VISIBLE),
    ("invisible", sym.INVISIBLE),
    ("visibleparam", sym.VISIBLEPARAM),
    ("invisibleparam", sym.INVISIBLEPARAM),

    # Special-case instructions
    ("tableswitch", sym.TABLESWITCH),
    ("lookupswitch", sym.LOOKUPSWITCH),
    ("default", sym.DEFAULT),

    # Access flags
    ("public", sym.PUBLIC),
    ("private", sym.PRIVATE),
    ("protected", sym.PROTECTED),
    ("static", sym.STATIC),
    ("final", sym.FINAL),
    ("synchronized", sym.SYNCHRONIZED),
    ("volatile", sym.VOLATILE),
    ("transient", sym.TRANSIENT),
    ("native", sym.NATIVE),
    ("interface", sym.INTERFACE),
    ("abstract", sym.ABSTRACT),

    ("annotation", sym.ANNOTATION),
    ("enum", sym.ENUM),
    ("bridge", sym.BRIDGE),
    ("varargs", sym.VARARGS),
    ("fpstrict", sym.STRICT),
    ("synthetic", sym.SYNTHETIC),
])


# ---------------------------------------------------------------------------
# ScannerUtils
# ---------------------------------------------------------------------------

_FLOAT_MAX = 3.4028234663852886e+38      # (double) Float.MAX_VALUE
_FLOAT_MIN = 1.401298464324817e-45       # (float) Float.MIN_VALUE


def convert_int(s, radix):
    """Converts a string of a given radix to an Integer or a Long (uses
    the smallest format that will hold the number)."""
    x = parse_long(s, radix)
    if -0x80000000 <= x <= 0x7FFFFFFF:
        return JavaInteger(x)
    return JavaLong(x)


def convert_number(s):
    """Converts a string to a number (Integer, Float, Long or Double),
    using the smallest format that will hold the number.  Raises a
    JavaException (NumberFormatException) for malformed numbers."""
    if s.startswith("+"):
        return JavaInteger(parse_int(s[1:]))
    if s.startswith("0x"):
        # base 16 integer
        return convert_int(s[2:], 16)
    elif '.' in s:
        # make a double
        dc = parse_double(s)
        # if the number has the suffix 'd' force a double value
        if not s.endswith("d"):
            # see if it will fit into a float...
            if dc <= _FLOAT_MAX and dc >= _FLOAT_MIN:
                return JavaFloat(to_float32(dc))
            # if not, return a double
        return JavaDouble(dc)
    else:
        # assume long or int in base 10
        return convert_int(s, 10)


def convert_dots(orig_name):
    """Maps '.' characters to '/' characters in a string."""
    return orig_name.replace('.', '/')


def convert_chars(orig_name, chars, to_char):
    """Maps all characters in chars to to_char in a string."""
    return ''.join(to_char if c in chars else c for c in orig_name)


def split_class_method_signature(name):
    """Splits a string like "a/b/c/d(xyz)v" into the three strings
    "a/b/c", "d" and "(xyz)v"."""
    pos = 0
    sigpos = 0
    for i, c in enumerate(name):
        if c == '.' or c == '/':
            pos = i
        elif c == '(':
            sigpos = i
            break
    try:
        return (convert_dots(substring(name, 0, pos)),
                substring(name, pos + 1, sigpos),
                convert_dots(substring(name, sigpos)))
    except JavaException:
        raise JavaException("java.lang.IllegalArgumentException",
                            "malformed signature : " + name)


def split_class_field(name):
    """Splits a string like "java/lang/System/out" into the two strings
    "java/lang/System" and "out".  The first one is None if the string
    contains no '/'."""
    pos = -1
    for i, c in enumerate(name):
        if c == '.' or c == '/':
            pos = i
    if pos == -1:       # no '/' in string
        return None, name
    return convert_dots(name[:pos]), name[pos + 1:]


def split_method_signature(name):
    """Splits a string like "main(Ljava/lang/String;)V" into the two
    strings "main" and "(Ljava/lang/String;)V"."""
    sigpos = name.find('(')
    if sigpos < 0:
        sigpos = 0
    return name[:sigpos], convert_dots(name[sigpos:])


# ---------------------------------------------------------------------------
# the scanner
# ---------------------------------------------------------------------------

_WHITESPACE = frozenset([32, 10, 9, 13])           # " \n\t\r"
_SEPARATORS = frozenset([32, 10, 9, 13, 58, 61, -1])   # + ":=" and EOF
_NUMBER_START = frozenset(map(ord, "-+0123456789."))

_ESCAPES = {ord('n'): '\n', ord('r'): '\r', ord('t'): '\t', ord('f'): '\f',
            ord('b'): '\b', ord('"'): '"', ord("'"): "'", ord('\\'): '\\'}


def whitespace(c):
    return c in _WHITESPACE


def separator(c):
    return c in _SEPARATORS


class Scanner(object):
    def __init__(self, text):
        """``text`` is the contents of the source file as a Java string."""
        self._inp = text
        self._pos = 0
        self._len = len(text)
        # used for error reporting to print out where an error is
        self.line_num = 1
        self.token_line_num = 0
        self.char_num = 0
        self.int_char_num = 0
        self.int_line_num = 0
        self._line = []
        self.int_line = None
        # used by the .set directive to define new variables
        self.dict = {}
        # As in the Java version, the same token object is returned every
        # time a reserved word is read (the parser stores its state in it).
        # The Java version shares them between all scanners; here every
        # scanner has its own, so that scanners can be used concurrently.
        self._reserved = dict((name, Token(num))
                              for name, num in RESERVED_WORDS.items())
        self.next_char = 0      # no start comment
        self._skip_empty_lines()
        if self.next_char == -1:
            raise JasError("empty source file")

    @property
    def line(self):
        """the part of the current line that has been read so far"""
        return ''.join(self._line)

    def _advance(self):
        """Advances the input by one character."""
        if self._pos < self._len:
            c = ord(self._inp[self._pos])
            self._pos += 1
        else:
            c = -1
        self.next_char = c
        if c == -1:             # EOF
            if self.char_num == 0:
                self.char_num = -1
                del self._line[:]
                return
            self.next_char = c = 10
        if c == 10:             # a new line
            self.line_num += 1
            self.char_num = 0
            del self._line[:]
            return
        self._line.append(chr(c))
        self.char_num += 1

    def _skip_empty_lines(self):
        while True:
            if self.next_char != 59:            # ';'
                self._advance()
                while self.next_char in _WHITESPACE:
                    self._advance()
                if self.next_char != 59:
                    return
            while True:
                self._advance()
                if self.next_char == -1:
                    return
                if self.next_char == 10:
                    break

    def _uni_escape(self):
        res = 0
        for _ in range(4):
            self._advance()
            if self.next_char == -1:
                return '\0'
            tmp = java_digit(self.next_char, 16)
            if tmp == -1:
                raise JasError("Bad '\\u' escape sequence")
            res = (res << 4) | tmp
        return chr(res)

    def _name_escape(self):
        self._advance()
        if self.next_char != 117:               # 'u'
            raise JasError("Only '\\u' escape sequence allowed in names")
        chval = self._uni_escape()
        if self.next_char == -1:
            raise JasError("Left over '\\u' escape sequence")
        return chval

    def next_token(self):
        """Recognizes and returns the next complete token."""
        self.token_line_num = self.line_num

        while True:
            c = self.next_char

            if c == 59 or c == 10:              # a comment or a new line
                # return single SEP token (skip multiple newlines
                # interspersed with whitespace or comments)
                self._skip_empty_lines()
                self.token_line_num = self.line_num
                return Token(sym.SEP)

            if c == -1:                         # EOF token
                self.char_num = -1
                return Token(sym.EOF)

            if c in _NUMBER_START:              # a number
                return self._read_number()

            if c == 34:                         # '"': quoted string
                return self._read_string()

            if c == 39:                         # "'": quoted name
                return self._read_quoted_name()

            if c == 32 or c == 9 or c == 13:    # whitespace
                self._advance()
                continue

            if c == 61:                         # '='
                self._advance()
                return Token(sym.EQ)

            if c == 58:                         # ':'
                self._advance()
                return Token(sym.COLON)

            return self._read_word()

    def _read_number(self):
        chars = []
        while True:
            chars.append(chr(self.next_char))
            self._advance()
            if self.next_char in _SEPARATORS:
                break
        s = ''.join(chars)

        # This catches directives like ".method"
        tok = self._reserved.get(s)
        if tok is not None:
            return tok

        try:
            num = convert_number(s)
        except JavaException as e:
            if e.java_class != "java.lang.NumberFormatException":
                raise
            if s[0] != '.':
                raise JasError("Badly formatted number")
            raise JasError("Unknown directive or badly formed number.")

        if isinstance(num, JavaInteger):
            self.int_line = self.line
            self.int_line_num = self.token_line_num
            self.int_char_num = self.char_num
            return Token(sym.Int, int(num))
        return Token(sym.Num, num)

    def _read_string(self):
        chars = []
        already = False
        while True:
            if already:
                already = False
            else:
                self._advance()

            c = self.next_char
            if c == 34:                         # closing '"'
                self._advance()
                return Token(sym.Str, ''.join(chars))

            if c == -1:
                raise JasError("Unterminated string")

            chval = chr(c)
            if c == 92:                         # '\\'
                self._advance()
                c = self.next_char
                if c == -1:
                    already = True
                    continue
                elif c in _ESCAPES:
                    chval = _ESCAPES[c]
                elif c == 117:                  # 'u'
                    chval = self._uni_escape()
                    if self.next_char == -1:
                        already = True
                        continue
                elif 48 <= c <= 55:             # octal escape
                    res = c & 7
                    self._advance()
                    c = self.next_char
                    if c < 48 or c > 55:
                        already = True
                    else:
                        res = res * 8 + (c & 7)
                        self._advance()
                        c = self.next_char
                        if c < 48 or c > 55:
                            already = True
                        else:
                            val = res * 8 + (c & 7)
                            if val >= 0x100:
                                already = True
                            else:
                                res = val
                    chval = chr(res)
                else:
                    raise JasError("Bad backslash escape sequence")
            chars.append(chval)

    def _read_quoted_name(self):
        # quotation for overloading reserved words
        chars = []
        while True:
            self._advance()
            c = self.next_char
            if c in _SEPARATORS:
                raise JasError("Unterminated ''-enclosed name")
            if c == 39:
                if not chars:
                    raise JasError("Empty ''-enclosed name")
                self._advance()             # skip close quote
                if self.next_char not in _SEPARATORS:
                    raise JasError("Not separator after ''-enclosed name")
                return Token(sym.Word, ''.join(chars))
            chval = chr(c)
            if c == 92:
                chval = self._name_escape()
            chars.append(chval)

    def _read_word(self):
        # read up until a separator character
        chars = []
        only_name = False
        while True:
            chval = chr(self.next_char)
            if self.next_char == 92:            # '\\'
                chval = self._name_escape()
                only_name = True
            chars.append(chval)
            self._advance()
            if self.next_char in _SEPARATORS:
                break
        s = ''.join(chars)

        if not only_name:
            # Jasmin keyword or directive ?
            tok = self._reserved.get(s)
            if tok is not None:
                return tok

            # is it a JVM instruction ?
            if insninfo.contains(s):
                return Token(sym.Insn, s)

            if s[0] == '$':
                rest = s[1:]
                first = char_at(rest, 0)
                if first == '-' or first == '+':
                    neg = first == '-'
                    rest = rest[1:]
                    radix = 10
                    if rest.startswith("0x"):
                        radix = 16
                        rest = rest[2:]
                    try:
                        n = parse_int(rest, radix)
                    except JavaException:
                        raise JasError("Badly relative offset number")
                    if neg:
                        n = int(JavaInteger(-n))
                    return Token(sym.Relative, n)
                # Perform variable substitution
                v = self.dict.get(rest)
                if v is not None:
                    return v

        # Unrecognized string token (e.g. a classname)
        return Token(sym.Word, s)
