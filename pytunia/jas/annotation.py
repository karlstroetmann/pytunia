"""
Annotations (port of jas.Annotation, jas.AnnotationElement,
jas.AnnotationAttr, jas.AnnotParamAttr and jas.AnnotDefAttr).
"""

from .cp import CP, AsciiCP, IntegerCP, FloatCP, DoubleCP, LongCP
from .errors import JasError
from ..javacompat import (JavaInteger, JavaLong, JavaFloat, JavaDouble,
                          char_at)


def parser_error():
    raise JasError("internal logic error in annotation parsing")


class Annotation(CP):
    """An annotation.  It is a CP subclass so that it can be stored as
    the value of an annotation element, but it is never added to the
    constant pool itself."""

    def __init__(self, type_cp=None, parent=None):
        self.type = type_cp
        self.parent = parent
        self.field = None
        self.fields = []

    @classmethod
    def named(cls, type_name):
        return cls(AsciiCP(type_name))

    def nest_annotation(self):
        if self.field is None:
            parser_error()
        tmp = Annotation(self.field.nest_type(), self)
        self.field.add_value(tmp)
        return tmp

    def end_annotation(self):
        if self.field is not None:
            self.field.done()
            self.field = None
        return self.parent

    def add_field(self, name, type_, add):
        if self.type is None and len(self.fields) != 0:
            parser_error()
        if self.field is not None:
            self.field.done()
            self.field = None
        if (name is None) != (self.type is None):
            parser_error()
        self.field = AnnotationElement(name, type_, add)
        self.fields.append(self.field)

    def add_value(self, value):
        if self.field is None:
            parser_error()
        self.field.add_value(value)

    def resolve(self, env):
        if self.type is not None:
            env.add_cp_item(self.type)
        for f in self.fields:
            f.resolve(env)

    def size(self):
        if self.field is not None:
            parser_error()
        length = 2 + 2
        if self.type is None:
            if len(self.fields) != 1:
                parser_error()
            length = 0
        for f in self.fields:
            length += f.size()
        return length

    def write(self, env, out):
        if self.field is not None:
            parser_error()
        if self.type is not None:
            out.write_short(env.get_cp_index(self.type))
            out.write_short(len(self.fields))
        elif len(self.fields) != 1:
            parser_error()
        for f in self.fields:
            f.write(env, out)


TYPE_INT = 'I'      # integer
TYPE_BYTE = 'B'     # signed byte
TYPE_CHAR = 'C'     # unicode character
TYPE_SHORT = 'S'    # signed short
TYPE_BOOL = 'Z'     # boolean true or false
TYPE_FLOAT = 'F'    # single precision IEEE float
TYPE_DOUBLE = 'D'   # double precision IEEE float
TYPE_LONG = 'J'     # long integer
TYPE_ARRAY = '['
TYPE_STRING = 's'   # constant string
TYPE_CLASS = 'c'    # return type descriptor
TYPE_ENUM = 'e'     # enum constant (type + name)
TYPE_ANNOT = '@'    # nested annotation

_SIMPLE_TYPES = 'IBCSZFDJsc'


def _bad_signature():
    raise JasError("invalid type signature for annotation field")


class AnnotationElement(object):
    def __init__(self, name, type_, exttype):
        self.name = None if name is None else AsciiCP(name)
        self.values = []
        self.array = False
        self.sign = char_at(type_, 0)
        if self.sign != TYPE_ARRAY:
            if len(type_) != 1:
                _bad_signature()
        else:
            self.array = True
            if len(type_) != 2:
                _bad_signature()
            self.sign = type_[1]
        if self.sign in (TYPE_ENUM, TYPE_ANNOT):
            if exttype is None:
                _bad_signature()
            self.exttype = AsciiCP(exttype)
        elif self.sign in _SIMPLE_TYPES:
            if exttype is not None:
                _bad_signature()
            self.exttype = None
        else:
            _bad_signature()

    def add_value(self, value):
        if value is None:
            parser_error()
        if not self.array and len(self.values) != 0:
            raise JasError("too many values for nonarray annotation "
                           "field type")
        cp = None
        sign = self.sign
        if sign in 'CZBSI':
            if isinstance(value, JavaInteger):
                val = int(value)
                badval = False
                if sign == TYPE_BOOL:
                    badval = val < 0 or val > 1
                elif sign == TYPE_CHAR:
                    badval = val < 0 or val > 0xFFFF
                elif sign == TYPE_BYTE:
                    badval = val < -128 or val > 127
                elif sign == TYPE_SHORT:
                    badval = val < -32768 or val > 32767
                if badval:
                    raise JasError("annotation field value exceed range "
                                   "of type")
                cp = IntegerCP(val)
        elif sign == TYPE_FLOAT:
            if isinstance(value, JavaFloat):
                cp = FloatCP(float(value))
        elif sign == TYPE_DOUBLE:
            if isinstance(value, (JavaDouble, JavaFloat)):
                cp = DoubleCP(float(value))
        elif sign == TYPE_LONG:
            if isinstance(value, (JavaLong, JavaInteger)):
                cp = LongCP(int(value))
        elif sign in (TYPE_STRING, TYPE_CLASS, TYPE_ENUM):
            if isinstance(value, str):
                if sign == TYPE_CLASS:
                    # a descriptor: pytunia converts its dots to slashes,
                    # Jasmin 2.4 does not (see README)
                    value = value.replace('.', '/')
                cp = AsciiCP(value)
        elif sign == TYPE_ANNOT:
            if isinstance(value, Annotation):
                cp = value
        if cp is None:
            raise JasError("incompatible value for annotation field type")
        self.values.append(cp)

    def nest_type(self):
        if self.sign != TYPE_ANNOT:
            parser_error()
        return self.exttype

    def done(self):
        n = len(self.values)
        if n == 1:
            return
        if n > 1 and self.array:
            return
        parser_error()

    def resolve(self, env):
        if self.name is not None:
            env.add_cp_item(self.name)
        if self.sign == TYPE_ENUM:
            env.add_cp_item(self.exttype)
        for cp in self.values:
            if self.sign != TYPE_ANNOT:
                env.add_cp_item(cp)
            else:
                cp.resolve(env)

    def size(self):
        self.done()
        if self.sign == TYPE_ANNOT:
            length = len(self.values)   # tags
            for a in self.values:
                length += a.size()
        else:
            length = 1 + 2
            if self.sign == TYPE_ENUM:
                length += 2
            length *= len(self.values)
        if self.array:
            length += 1 + 2
        if self.name is not None:
            length += 2
        return length

    def write(self, env, out):
        self.done()
        if self.name is not None:
            out.write_short(env.get_cp_index(self.name))
        if self.array:
            out.write_byte(ord(TYPE_ARRAY))
            out.write_short(len(self.values))
        ident = 0
        if self.sign == TYPE_ENUM:
            ident = env.get_cp_index(self.exttype)
        for cp in self.values:
            out.write_byte(ord(self.sign))
            if self.sign == TYPE_ANNOT:
                cp.write(env, out)
            else:
                if self.sign == TYPE_ENUM:
                    out.write_short(ident)
                out.write_short(env.get_cp_index(cp))


class AnnotationAttr(object):
    def __init__(self, visible):
        self.attr = AsciiCP("RuntimeVisibleAnnotations" if visible
                            else "RuntimeInvisibleAnnotations")
        self.anns = []

    def add(self, annotation):
        self.anns.append(annotation)

    def resolve(self, env):
        env.add_cp_item(self.attr)
        for a in self.anns:
            a.resolve(env)

    def write(self, env, out):
        out.write_short(env.get_cp_index(self.attr))
        length = 2
        for a in self.anns:
            length += a.size()
        out.write_int(length)
        out.write_short(len(self.anns))
        for a in self.anns:
            a.write(env, out)


class AnnotParamAttr(object):
    def __init__(self, visible):
        self.attr = AsciiCP("RuntimeVisibleParameterAnnotations" if visible
                            else "RuntimeInvisibleParameterAnnotations")
        self.anns = []          # list of (list of Annotation or None)

    def add(self, annotation, paramnum):
        ap = None
        top = len(self.anns)
        if paramnum < top:
            ap = self.anns[paramnum]
        if ap is None:
            if paramnum >= top:
                self.anns.extend([None] * (paramnum + 1 - top))
            ap = self.anns[paramnum] = []
        ap.append(annotation)

    def resolve(self, env):
        env.add_cp_item(self.attr)
        for ap in self.anns:
            if ap is None:
                continue
            for a in ap:
                a.resolve(env)

    def write(self, env, out):
        out.write_short(env.get_cp_index(self.attr))
        top = len(self.anns)
        length = 1 + 2 * top
        for ap in self.anns:
            if ap is not None:
                for a in ap:
                    length += a.size()
        out.write_int(length)
        out.write_byte(top)
        for ap in self.anns:
            if ap is None:
                out.write_short(0)
            else:
                out.write_short(len(ap))
                for a in ap:
                    a.write(env, out)


class AnnotDefAttr(object):
    attr = AsciiCP("AnnotationDefault")

    def __init__(self):
        self.ann = Annotation()

    def get(self):
        return self.ann

    def resolve(self, env):
        env.add_cp_item(self.attr)
        self.ann.resolve(env)

    def write(self, env, out):
        out.write_short(env.get_cp_index(self.attr))
        out.write_int(self.ann.size())
        self.ann.write(env, out)
