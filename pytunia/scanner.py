"""
The tokenizer for Jasmin source files (port of jasmin.Scanner and
jasmin.ScannerUtils).

The scanner works on a Java string, i.e. a sequence of UTF-16 code
units (see javacompat.to_java_string).  It returns the tokens as
larkita.Token objects; their types are the terminals of the grammar
jasmin.g.  The reserved words of Jasmin are the string literals of the
grammar (parser.KEYWORDS).
"""

from larkita import Token

from . import insninfo
from .jas.errors import JasError
from .javacompat import (JavaException, JavaInteger, JavaLong, JavaFloat,
                         JavaDouble, parse_int, parse_long, parse_double,
                         java_digit, substring, char_at, to_float32)
from .parser import KEYWORDS


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


class Scanner(object):
    def __init__(self, text):
        """``text`` is the contents of the source file as a Java string."""
        self._inp = text
        self._pos = 0
        self._len = len(text)
        # the position of next_char (used for tokens and error messages):
        # its line and the number of characters of the line read so far
        # (-1 at the end of the input).  When next_char is a line break,
        # line_num is already the number of the next line.
        self.line_num = 1
        self.char_num = 0
        self._prev_line_length = 0
        # the line of the first token of the current statement
        self._statement_line = None
        # where an error is reported instead of the current position
        self._error_at = None
        # the variables defined with .set (see _read_word)
        self._variables = set()
        self._after_set = False
        self.next_char = 0      # no start comment
        self._skip_empty_lines()
        if self.next_char == -1:
            raise JasError("empty source file")

    def position(self):
        """The line and column (both counted from 1) of the character that
        the scanner is looking at; the column is None at the end of the
        input."""
        if self.next_char == 10:
            return self.line_num - 1, self._prev_line_length + 1
        if self.char_num < 0:
            return self.line_num, None
        return self.line_num, self.char_num

    def error_position(self):
        """The position where an error of the scanner is reported: the start
        of an unterminated string, otherwise the current position."""
        return self._error_at or self.position()

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
                return
            self.next_char = c = 10
        if c == 10:             # a new line
            self._prev_line_length = self.char_num
            self.line_num += 1
            self.char_num = 0
            return
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

    def tokens(self):
        """Returns an iterator over all tokens of the input."""
        while True:
            token = self.next_token()
            if token is None:
                return
            yield token

    def next_token(self):
        """Recognizes and returns the next token, or None at the end of the
        input."""
        while True:
            c = self.next_char

            if c == 59 or c == 10:              # a comment or a new line
                # return a single EOL token (skip multiple newlines
                # interspersed with whitespace or comments)
                line, column = self.position()
                statement_line = self._statement_line or line
                self._statement_line = None
                self._skip_empty_lines()
                return Token('EOL', statement_line, line=line, column=column)

            if c == -1:                         # end of the input
                return None

            if c == 32 or c == 9 or c == 13:    # whitespace
                self._advance()
                continue
            break

        line, column = self.position()
        if self._statement_line is None:
            self._statement_line = line

        if c in _NUMBER_START:                  # a number
            token_type, value = self._read_number()
        elif c == 34:                           # '"': quoted string
            token_type, value = 'STR', self._read_string((line, column))
        elif c == 39:                           # "'": quoted name
            token_type, value = 'WORD', self._read_quoted_name()
        elif c == 61 or c == 58:                # '=' or ':'
            self._advance()
            value = chr(c)
            token_type = KEYWORDS[value]
        else:
            token_type, value = self._read_word()

        if self._after_set and token_type == 'WORD':
            self._variables.add(value)
        self._after_set = token_type == KEYWORDS['.set']
        return Token(token_type, value, line=line, column=column)

    def _read_number(self):
        chars = []
        while True:
            chars.append(chr(self.next_char))
            self._advance()
            if self.next_char in _SEPARATORS:
                break
        s = ''.join(chars)

        # This catches directives like ".method"
        if s in KEYWORDS:
            return KEYWORDS[s], s

        try:
            num = convert_number(s)
        except JavaException as e:
            if e.java_class != "java.lang.NumberFormatException":
                raise
            if s[0] != '.':
                raise JasError("Badly formatted number")
            raise JasError("Unknown directive or badly formed number.")

        if isinstance(num, JavaInteger):
            return 'INT', int(num)
        return 'NUM', num

    def _read_string(self, start):
        """Reads a string that starts at the position ``start``."""
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
                return ''.join(chars)

            if c == -1:
                self._error_at = start
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
                return ''.join(chars)
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
            if s in KEYWORDS:
                return KEYWORDS[s], s

            # is it a JVM instruction ?
            if insninfo.contains(s):
                return 'INSN', s

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
                    return 'RELATIVE', n
                # Jasmin 2.4 substitutes the variables defined with
                # ".set name value" by a token that the parser takes as
                # ".method", so a program that uses one is not accepted.
                if rest in self._variables:
                    raise JasError("Variable substitution is not supported: "
                                   + s)

        # Unrecognized string token (e.g. a classname)
        return 'WORD', s
