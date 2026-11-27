"""
Types written as in Java (new in pytunia, not in Jasmin).

Besides the descriptors of the JVM, pytunia accepts types that are written
as in Java, with fully qualified class names:

    Java notation                         descriptor of the JVM
    int                                   I
    java.lang.String[]                    [Ljava/lang/String;
    main(java.lang.String[]) void         main([Ljava/lang/String;)V
    max(int, int) int                     max(II)I

The parameters of a method are separated by commas, and its return type
follows the closing parenthesis, usually after a blank.  The blanks split
a signature into several words; parser.join_signatures joins them again.

Both notations can be mixed.  A word that is a valid descriptor keeps its
meaning as a descriptor, so the sources of Jasmin are translated as before:
"I" is the type int, not a class I in the default package, and a parameter
list without commas like "(IJ)" is a list of descriptors (int and long).
A word that is neither a descriptor nor a type in Java notation is left
unchanged, as Jasmin does.

The functions below expect class names in either form (java.lang.String or
java/lang/String) and return the descriptors of the JVM, with slashes.
"""

import re

from .jas.errors import JasError

__all__ = ["field_descriptor", "method_descriptor", "class_operand"]

_PRIMITIVES = {"boolean": "Z", "byte": "B", "char": "C", "short": "S",
               "int": "I", "long": "J", "float": "F", "double": "D"}

_BASE_TYPES = "BCDFIJSZ"

# a type in Java notation: a primitive type or a class name (identifiers
# separated by slashes, after the dots have been converted), followed by
# any number of "[]"
_IDENTIFIER = r"(?:[^\W\d]|\$)[\w$]*"
_JAVA_TYPE = re.compile(r"(%s(?:/%s)*)((?:\[\])*)"
                        % (_IDENTIFIER, _IDENTIFIER))


def _descriptor_end(s, i):
    """If a field descriptor starts at position i of s, the position after
    it, else -1."""
    while i < len(s) and s[i] == '[':
        i += 1
    if i == len(s):
        return -1
    if s[i] in _BASE_TYPES:
        return i + 1
    if s[i] == 'L':
        end = s.find(';', i)
        if end > i + 1:
            return end + 1
    return -1


def _is_descriptor(s):
    """True if s is a field descriptor, e.g. "I" or "[Ljava/lang/String;"."""
    return _descriptor_end(s, 0) == len(s)


def _is_descriptor_list(s):
    """True if s is a sequence of field descriptors, e.g. "ILjava/lang/X;"."""
    i = 0
    while i < len(s):
        i = _descriptor_end(s, i)
        if i < 0:
            return False
    return True


def _java_type(s, void_allowed=False):
    """The descriptor of the type s in Java notation (with slashes in class
    names), or None if s is no such type."""
    match = _JAVA_TYPE.fullmatch(s)
    if match is None:
        return None
    name, brackets = match.groups()
    dimensions = len(brackets) // 2
    if name == "void":
        return "V" if void_allowed and dimensions == 0 else None
    return "[" * dimensions + _PRIMITIVES.get(name, "L" + name + ";")


def _type(s, void_allowed=False):
    """The descriptor of s, which is a descriptor or a type in Java
    notation, or None."""
    if _is_descriptor(s) or (void_allowed and s == "V"):
        return s
    return _java_type(s, void_allowed)


def field_descriptor(s):
    """The descriptor of the type s of a field or a local variable, e.g.
    "Ljava/io/PrintStream;" for "java.io.PrintStream"."""
    s = s.replace('.', '/')
    descriptor = _type(s)
    return s if descriptor is None else descriptor


def method_descriptor(s):
    """The descriptor of the parameters and the return type s of a method,
    e.g. "(II)I" for "(int, int) int".  Raises JasError if s is not
    well-formed and contains a blank, which only the Java notation can
    produce."""
    s = s.replace('.', '/')
    descriptor = _method_descriptor(s)
    if descriptor is not None:
        return descriptor
    if any(c.isspace() for c in s):
        raise JasError("malformed method signature: " + s.replace('/', '.'))
    return s


def _method_descriptor(s):
    if not s.startswith('('):
        return None
    close = s.find(')')
    if close < 0:
        return None
    parameters = s[1:close].strip()
    if ',' in parameters:
        descriptors = [_type(p.strip()) for p in parameters.split(',')]
        if None in descriptors:
            return None
        parameters = "".join(descriptors)
    elif parameters and not _is_descriptor_list(parameters):
        parameters = _java_type(parameters)
        if parameters is None:
            return None
    result = _type(s[close + 1:].strip(), void_allowed=True)
    if result is None:
        return None
    return "(" + parameters + ")" + result


def class_operand(s):
    """The operand of an instruction like checkcast or anewarray, which is a
    class name or the descriptor of an array type: "java/lang/String" stays
    as it is, but "java.lang.String[]" becomes "[Ljava/lang/String;"."""
    s = s.replace('.', '/')
    if s.endswith("[]"):
        descriptor = _java_type(s)
        if descriptor is not None:
            return descriptor
    return s
