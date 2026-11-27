"""
Simple class file attributes (port of jas.ExceptAttr, jas.ConstAttr,
jas.SourceAttr, jas.SignatureAttr, jas.DeprecatedAttr,
jas.SourceDebugExtensionAttr, jas.EnclosingMethodAttr, jas.GenericAttr,
jas.InnerClass and jas.InnerClassesAttr).
"""

from .cp import AsciiCP, ClassCP, NameTypeCP
from .errors import JasError
from ..javacompat import DataOutput, from_java_string


class ExceptAttr(object):
    attr = AsciiCP("Exceptions")

    def __init__(self):
        self.cps = []

    def add_exception(self, cp):
        self.cps.append(cp)

    def resolve(self, env):
        env.add_cp_item(self.attr)
        for cp in self.cps:
            env.add_cp_item(cp)

    def write(self, env, out):
        out.write_short(env.get_cp_index(self.attr))
        out.write_int(len(self.cps) * 2 + 2)
        out.write_short(len(self.cps))
        for cp in self.cps:
            out.write_short(env.get_cp_index(cp))


class ConstAttr(object):
    attr = AsciiCP("ConstantValue")

    def __init__(self, val):
        self.val = val

    def resolve(self, env):
        env.add_cp_item(self.val)
        env.add_cp_item(self.attr)

    def write(self, env, out):
        out.write_short(env.get_cp_index(self.attr))
        out.write_int(2)
        out.write_short(env.get_cp_index(self.val))


class SourceAttr(object):
    attr = AsciiCP("SourceFile")

    def __init__(self, name):
        self.name = name if isinstance(name, AsciiCP) else AsciiCP(name)

    def resolve(self, env):
        env.add_cp_item(self.attr)
        env.add_cp_item(self.name)

    def write(self, env, out):
        out.write_short(env.get_cp_index(self.attr))
        out.write_int(2)
        out.write_short(env.get_cp_index(self.name))


class SignatureAttr(object):
    attr = AsciiCP("Signature")

    def __init__(self, signature):
        self.signature = (signature if isinstance(signature, AsciiCP)
                          else AsciiCP(signature))

    def resolve(self, env):
        env.add_cp_item(self.attr)
        env.add_cp_item(self.signature)

    def write(self, env, out):
        out.write_short(env.get_cp_index(self.attr))
        out.write_int(2)
        out.write_short(env.get_cp_index(self.signature))


class DeprecatedAttr(object):
    attr = AsciiCP("Deprecated")

    def resolve(self, env):
        env.add_cp_item(self.attr)

    def write(self, env, out):
        out.write_short(env.get_cp_index(self.attr))
        out.write_int(0)


class SourceDebugExtensionAttr(object):
    attr = AsciiCP("SourceDebugExtension")

    def __init__(self, debug):
        self.debug = debug

    def append(self, debug):
        self.debug += debug

    def resolve(self, env):
        env.add_cp_item(self.attr)

    def write(self, env, out):
        out.write_short(env.get_cp_index(self.attr))
        buf = DataOutput()
        buf.write_utf(self.debug)
        # the (u4) attribute length is formed by these two zero bytes and
        # the (u2) length written by writeUTF
        out.write_short(0)
        out.write(buf.getvalue())


class EnclosingMethodAttr(object):
    attr = AsciiCP("EnclosingMethod")

    def __init__(self, cls, mtd, dsc):
        self.cls = cls
        self.mtd = mtd
        self.dsc = dsc
        self.clscp = ClassCP(cls)
        self.ntcp = None
        if mtd is not None and dsc is not None:
            self.ntcp = NameTypeCP(mtd, dsc)

    def resolve(self, env):
        env.add_cp_item(self.attr)
        env.add_cp_item(self.clscp)     # add the CONSTANT_Class
        self.clscp.resolve(env)         # add the CONSTANT_Utf8 for the name
        if self.ntcp is not None:
            env.add_cp_item(self.ntcp)  # add the CONSTANT_NameAndType
            self.ntcp.resolve(env)      # add the two CONSTANT_Utf8

    def write(self, env, out):
        out.write_short(env.get_cp_index(self.attr))
        out.write_int(4)
        out.write_short(env.get_cp_index(self.clscp))
        out.write_short(0 if self.ntcp is None
                        else env.get_cp_index(self.ntcp))


class GenericAttr(object):
    """An attribute with uninterpreted contents."""

    def __init__(self, name, data):
        self.attr_name = name if isinstance(name, AsciiCP) else AsciiCP(name)
        self.data = bytes(data)

    @classmethod
    def from_file(cls, name, filename):
        """Make an attribute whose contents is read from a file."""
        try:
            with open(from_java_string(filename), 'rb') as f:
                data = f.read()
        except (OSError, ValueError):
            raise JasError("Generic atribute file " + filename +
                           " not found")
        return cls(name, data)

    def resolve(self, env):
        env.add_cp_item(self.attr_name)

    def size(self):
        return 2 + 4 + len(self.data)

    def write(self, env, out):
        out.write_short(env.get_cp_index(self.attr_name))
        out.write_int(len(self.data))
        out.write(self.data)


class InnerClass(object):
    @staticmethod
    def size():
        return 4 * 2

    def __init__(self, access, name, inner, outer):
        self.access = access
        self.name = None if name is None else AsciiCP(name)
        self.inner = None if inner is None else ClassCP(inner)
        self.outer = None if outer is None else ClassCP(outer)

    def resolve(self, env):
        if self.name is not None:
            env.add_cp_item(self.name)
        if self.inner is not None:
            env.add_cp_item(self.inner)
            self.inner.resolve(env)
        if self.outer is not None:
            env.add_cp_item(self.outer)
            self.outer.resolve(env)

    def write(self, env, out):
        out.write_short(0 if self.inner is None
                        else env.get_cp_index(self.inner))
        out.write_short(0 if self.outer is None
                        else env.get_cp_index(self.outer))
        out.write_short(0 if self.name is None
                        else env.get_cp_index(self.name))
        out.write_short(self.access)


class InnerClassesAttr(object):
    attr = AsciiCP("InnerClasses")

    def __init__(self):
        self.list = []

    def add_inner_class(self, item):
        self.list.append(item)

    def resolve(self, env):
        env.add_cp_item(self.attr)
        for ic in self.list:
            ic.resolve(env)

    def write(self, env, out):
        out.write_short(env.get_cp_index(self.attr))
        out.write_int(len(self.list) * InnerClass.size() + 2)
        out.write_short(len(self.list))
        for ic in self.list:
            ic.write(env, out)
