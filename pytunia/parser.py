"""
The parser for Jasmin source files.

The grammar is in jasmin.g.  The parser generator Larkita turns it into a
canonical LR(1) parser, which builds the abstract syntax tree of a source
file as a nested tuple (see translator.py for how the tree is used).  The
tokens come from pytunia's scanner (scanner.py).
"""

from larkita import Larkita, UnexpectedToken

__all__ = ["KEYWORDS", "UnexpectedToken", "parse", "syntax_error_message"]

# (no output file: the description of the LR automaton is not needed here)
_LARKITA = Larkita.open("jasmin.g", rel_to=__file__, lexer="basic",
                        out_file=False)

# the string literals of the grammar (the reserved words of Jasmin, ":" and
# "=") and the names of their terminals
KEYWORDS = _LARKITA.literals

_KEYWORD_TEXT = {name: text for text, name in KEYWORDS.items()}

# how the other terminals are described in syntax error messages
_DESCRIPTIONS = {
    "EOL": "end of line",
    "WORD": "name",
    "INSN": "instruction",
    "STR": "string",
    "INT": "integer",
    "NUM": "number",
    "RELATIVE": "relative offset",
    "$END": "end of file",
}


def parse(scanner):
    """Parses the tokens that ``scanner`` (a scanner.Scanner) returns and
    returns the abstract syntax tree.  Raises UnexpectedToken if there is a
    syntax error; errors of the scanner are raised as JasError."""
    return _LARKITA.parse_tokens(scanner.tokens())


def _describe(token_type):
    if token_type in _KEYWORD_TEXT:
        return "'%s'" % _KEYWORD_TEXT[token_type]
    return _DESCRIPTIONS.get(token_type, token_type)


def _describe_token(token):
    description = _describe(token.type)
    if token.type in ("WORD", "INSN", "STR"):
        description += " '%s'" % token
    elif token.type in ("INT", "NUM", "RELATIVE"):
        description += " " + token      # the token is the text of its value
    return description


def syntax_error_message(error):
    """The message for an UnexpectedToken exception, e.g.
    "Syntax error: unexpected name 'foo', expected integer"."""
    message = "Syntax error: unexpected " + _describe_token(error.token)
    expected = sorted(_describe(t) for t in error.expected)
    if expected and len(expected) <= 5:
        message += ", expected " + " or ".join(expected)
    return message
