"""
Constant pool entries (port of jas.CP and its subclasses).

Every entry has a ``uniq`` string.  The class environment stores the
entries in a hash table keyed by this string, which makes entries with
identical contents share a single slot in the constant pool.  The
strings are the same as in the Java implementation, because they also
determine the order in which the constant pool is written.
"""

from .constants import (CONSTANT_UTF8, CONSTANT_INTEGER, CONSTANT_FLOAT,
                        CONSTANT_LONG, CONSTANT_DOUBLE, CONSTANT_CLASS,
                        CONSTANT_STRING, CONSTANT_FIELD, CONSTANT_METHOD,
                        CONSTANT_INTERFACEMETHOD, CONSTANT_NAMEANDTYPE)
from ..javacompat import (null_pointer, float_to_string, double_to_string,
                          to_float32)


def _cat(s):
    """String concatenation semantics of Java (null -> "null")."""
    return "null" if s is None else s


class CP(object):
    """Base class of all constant pool entries."""
    uniq = None

    def get_uniq(self):
        return self.uniq

    def resolve(self, env):
        raise NotImplementedError

    def write(self, env, out):
        raise NotImplementedError


class AsciiCP(CP):
    """A CONSTANT_Utf8 entry."""

    def __init__(self, s):
        if s is None:
            raise null_pointer()
        self.uniq = s

    def resolve(self, env):
        return

    def __str__(self):
        return "AsciiCP: " + self.uniq

    def write(self, env, out):
        out.write_byte(CONSTANT_UTF8)
        out.write_utf(self.uniq)


class ClassCP(CP):
    """A CONSTANT_Class entry."""

    def __init__(self, name):
        self.uniq = "CLASS: #$%^#$" + _cat(name)
        self.name = AsciiCP(name)

    def resolve(self, env):
        env.add_cp_item(self.name)

    def write(self, env, out):
        out.write_byte(CONSTANT_CLASS)
        out.write_short(env.get_cp_index(self.name))


class StringCP(CP):
    """A CONSTANT_String entry."""

    def __init__(self, s):
        self.uniq = "String: @#$" + _cat(s)
        self.val = AsciiCP(s)

    def resolve(self, env):
        env.add_cp_item(self.val)

    def write(self, env, out):
        out.write_byte(CONSTANT_STRING)
        out.write_short(env.get_cp_index(self.val))


class IntegerCP(CP):
    """A CONSTANT_Integer entry."""

    def __init__(self, n):
        self.val = n
        self.uniq = "Integer: @#$" + str(n)

    def resolve(self, env):
        return

    def write(self, env, out):
        out.write_byte(CONSTANT_INTEGER)
        out.write_int(self.val)


class FloatCP(CP):
    """A CONSTANT_Float entry."""

    def __init__(self, n):
        self.val = to_float32(n)
        self.uniq = "Float: @#$" + float_to_string(self.val)

    def resolve(self, env):
        return

    def write(self, env, out):
        out.write_byte(CONSTANT_FLOAT)
        out.write_float(self.val)


class LongCP(CP):
    """A CONSTANT_Long entry."""

    def __init__(self, n):
        self.val = n
        self.uniq = "Long: @#$" + str(n)

    def resolve(self, env):
        return

    def write(self, env, out):
        out.write_byte(CONSTANT_LONG)
        out.write_long(self.val)


class DoubleCP(CP):
    """A CONSTANT_Double entry."""

    def __init__(self, n):
        self.val = float(n)
        self.uniq = "Double: @#$" + double_to_string(self.val)

    def resolve(self, env):
        return

    def write(self, env, out):
        out.write_byte(CONSTANT_DOUBLE)
        out.write_double(self.val)


class NameTypeCP(CP):
    """A CONSTANT_NameAndType entry."""

    def __init__(self, name, sig):
        self.uniq = "NT : @#$%" + _cat(name) + "SD#$" + _cat(sig)
        self.name = AsciiCP(name)
        self.sig = AsciiCP(sig)

    def resolve(self, env):
        env.add_cp_item(self.name)
        env.add_cp_item(self.sig)

    def write(self, env, out):
        out.write_byte(CONSTANT_NAMEANDTYPE)
        out.write_short(env.get_cp_index(self.name))
        out.write_short(env.get_cp_index(self.sig))


class _MemberCP(CP):
    tag = None

    def resolve(self, env):
        env.add_cp_item(self.clazz)
        env.add_cp_item(self.nt)

    def write(self, env, out):
        out.write_byte(self.tag)
        out.write_short(env.get_cp_index(self.clazz))
        out.write_short(env.get_cp_index(self.nt))


class FieldCP(_MemberCP):
    """A CONSTANT_Fieldref entry."""
    tag = CONSTANT_FIELD

    def __init__(self, clazz, name, sig):
        self.uniq = _cat(clazz) + "&%$#&" + _cat(name) + "*()#$" + _cat(sig)
        self.clazz = ClassCP(clazz)
        self.nt = NameTypeCP(name, sig)


class MethodCP(_MemberCP):
    """A CONSTANT_Methodref entry."""
    tag = CONSTANT_METHOD

    def __init__(self, cname, varname, sig):
        self.uniq = (_cat(cname) + "&%$91&" + _cat(varname) + "*(012$" +
                     _cat(sig))
        self.clazz = ClassCP(cname)
        self.nt = NameTypeCP(varname, sig)


class InterfaceCP(_MemberCP):
    """A CONSTANT_InterfaceMethodref entry."""
    tag = CONSTANT_INTERFACEMETHOD

    def __init__(self, cname, varname, sig):
        # (the Java version uses the same uniq format as FieldCP)
        self.uniq = (_cat(cname) + "&%$#&" + _cat(varname) + "*()#$" +
                     _cat(sig))
        self.clazz = ClassCP(cname)
        self.nt = NameTypeCP(varname, sig)
