"""
The parser for Jasmin source files.

The grammar is in jasmin.g.  The parser generator Larkita turns it into a
canonical LR(1) parser, which builds the abstract syntax tree of a source
file as a nested tuple (see translator.py for how the tree is used).  The
tokens come from pytunia's scanner (scanner.py), and join_signatures joins
the words of method signatures that are written in Java notation.
"""

from larkita import Larkita, Token, UnexpectedToken

from . import insninfo

__all__ = ["KEYWORDS", "UnexpectedToken", "join_signatures", "parse",
           "syntax_error_message"]

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
    return _LARKITA.parse_tokens(join_signatures(scanner.tokens()))


# the tokens that can be part of a signature in Java notation
_SIGNATURE_PARTS = ({"WORD", "INSN"} |
                    {name for text, name in KEYWORDS.items()
                     if text not in (":", "=")})


def join_signatures(tokens):
    """Joins the words of method signatures in Java notation (new in
    pytunia, see javatypes.py).

    The scanner splits words at blanks, so "max(int, int) int" arrives as
    the three words "max(int,", "int)" and "int".  In ".method",
    ".enclosing method" and the invoke instructions, the words of the
    signature are joined with single blanks: first until its parentheses
    are balanced, then, if it ends with ")", the word with the return
    type.  Jasmin rejects every source where this joins words."""
    tokens = iter(tokens)
    signature_follows = False
    pending = None
    while True:
        if pending is not None:
            token, pending = pending, None
        else:
            token = next(tokens, None)
            if token is None:
                return
        if signature_follows and token.type == "WORD":
            token, pending = _join_signature(token, tokens)
            signature_follows = False
            yield token
            if pending is None:
                return
            continue
        signature_follows = _signature_follows(token, signature_follows)
        yield token


def _signature_follows(token, before):
    """True if the next word after ``token`` is a method signature.
    ``before`` is the result for the token before ``token``."""
    if token.type in (KEYWORDS[".method"], KEYWORDS["method"]):
        return True
    if token.type == "INSN":
        return insninfo.get(token).args in ("method", "interface")
    # the access flags between ".method" and the signature
    return before and token.type in _KEYWORD_TEXT


def _join_signature(word, tokens):
    """Joins the signature that starts with ``word`` with the tokens that
    follow it.  Returns the joined word and the first token that is not
    part of it (None at the end of the input)."""
    parts = [str(word)]
    following = next(tokens, None)
    while following is not None and following.type in _SIGNATURE_PARTS:
        text = " ".join(parts)
        balanced = text.count("(") <= text.count(")")
        if balanced and not ("(" in text and text.endswith(")")):
            break                   # the signature is complete
        parts.append(str(following))
        following = next(tokens, None)
        if balanced:
            break                   # that was the return type
    if len(parts) == 1:
        return word, following
    return (Token("WORD", " ".join(parts), line=word.line,
                  column=word.column), following)


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
