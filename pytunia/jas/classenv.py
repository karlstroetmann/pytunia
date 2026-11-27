"""
The class being built, its methods and fields (port of jas.ClassEnv,
jas.Method and jas.Var).
"""

from . import constants as rc
from .annotation import Annotation, AnnotationAttr, AnnotParamAttr, \
    AnnotDefAttr, parser_error
from .attributes import SourceAttr, SourceDebugExtensionAttr, \
    EnclosingMethodAttr, SignatureAttr, InnerClassesAttr, InnerClass
from .cp import LongCP, DoubleCP
from .errors import JasError
from .insn import _cp_str, _short
from ..javacompat import JavaHashtable


class ClassEnv(object):
    def __init__(self):
        # Fill in reasonable defaults
        self.magic = rc.JAVA_MAGIC
        self.version_lo = rc.JAVA_MINOR_VERSION
        self.version_hi = rc.JAVA_VERSION
        self.this_class = None
        self.super_class = None
        self.class_access = 0
        # constant pool entries, keyed by their uniq strings
        self.cpe = JavaHashtable()
        self.cpe_index = None
        self.interfaces = []
        self.vars = []
        self.methods = []
        self.source = None
        self.signature = None
        self.debug = None
        self.enclosing = None
        self.depr = None
        self.innerclasses = None
        self.ann_vis = None
        self.ann_invis = None
        self.generic = []
        # attribute name and format of the stack map frames (set by the
        # first StackMap of the class)
        self.stackmap_attr = None
        self.stackmap_java6 = False

    def set_class(self, name):
        self.this_class = name
        self.add_cp_item(name)

    def set_super_class(self, name):
        self.super_class = name
        self.add_cp_item(name)

    def set_class_access(self, access):
        self.class_access = access

    def add_interface(self, ifc):
        self.add_cp_item(ifc)
        self.interfaces.append(ifc)

    def add_field(self, var):
        self.vars.append(var)
        var.resolve(self)

    def write(self, out):
        """Write the class file to the DataOutput ``out``."""
        # Headers
        out.write_int(self.magic)
        out.write_short(self.version_lo)
        out.write_short(self.version_hi)
        # make up indices for the constant pool entries
        curidx = 1
        self.cpe_index = {}
        entries = self.cpe.values()
        for tmp in entries:
            self.cpe_index[tmp.get_uniq()] = curidx
            curidx += 1
            if isinstance(tmp, (LongCP, DoubleCP)):
                curidx += 1
        out.write_short(curidx)
        # Now write out all the entries
        for now in entries:
            now.write(self, out)
        # Class hierarchy/access
        out.write_short(self.class_access)
        out.write_short(self.get_cp_index(self.this_class))
        out.write_short(self.get_cp_index(self.super_class))
        # interfaces
        out.write_short(len(self.interfaces))
        for c in self.interfaces:
            out.write_short(self.get_cp_index(c))
        # variables
        out.write_short(len(self.vars))
        for v in self.vars:
            v.write(self, out)
        # methods
        out.write_short(len(self.methods))
        for m in self.methods:
            m.write(self, out)
        # additional attributes
        attrs = [a for a in (self.source, self.debug, self.enclosing,
                             self.signature, self.innerclasses, self.depr,
                             self.ann_vis, self.ann_invis)
                 if a is not None]
        out.write_short(len(attrs) + len(self.generic))
        for a in attrs:
            a.write(self, out)
        for g in self.generic:
            g.write(self, out)

    def add_cp_item(self, cp):
        """Add an entry to the constant pool.  Entries are "uniquefied":
        an entry whose contents already exist is not added again."""
        uniq = cp.get_uniq()
        if uniq not in self.cpe:
            self.cpe.put(uniq, cp)
            # resolve it so it adds anything which it depends on
            cp.resolve(self)

    def set_source(self, source):
        if not isinstance(source, SourceAttr):
            source = SourceAttr(source)
        self.source = source
        source.resolve(self)

    def set_source_debug_extension(self, debug):
        if self.debug is not None:
            self.debug.append(debug)
        else:
            self.debug = SourceDebugExtensionAttr(debug)
            self.debug.resolve(self)

    def set_enclosing_method(self, cls, mtd, dsc):
        self.enclosing = EnclosingMethodAttr(cls, mtd, dsc)
        self.enclosing.resolve(self)

    def set_signature(self, sig):
        self.signature = SignatureAttr(sig)
        self.signature.resolve(self)

    def set_deprecated(self, depr):
        self.depr = depr
        depr.resolve(self)

    def add_generic_attr(self, g):
        self.generic.append(g)
        g.resolve(self)

    def add_inner_class(self, iacc, name, inner, outer):
        if self.innerclasses is None:
            self.innerclasses = InnerClassesAttr()
            self.innerclasses.resolve(self)
        ic = InnerClass(iacc, name, inner, outer)
        ic.resolve(self)
        self.innerclasses.add_inner_class(ic)

    def add_annotation(self, visible, clsname):
        ann = Annotation.named(clsname)
        aa = self.ann_vis if visible else self.ann_invis
        if aa is None:
            aa = AnnotationAttr(visible)
            if visible:
                self.ann_vis = aa
            else:
                self.ann_invis = aa
        aa.add(ann)
        return ann

    def end_header(self):
        if self.ann_vis is not None:
            self.ann_vis.resolve(self)
        if self.ann_invis is not None:
            self.ann_invis.resolve(self)

    def add_method(self, m):
        m.resolve(self)
        self.methods.append(m)

    def get_cp_index(self, cp):
        if self.cpe_index is None:
            raise JasError("Internal error: CPE index has not been generated")
        idx = self.cpe_index.get(cp.get_uniq())
        if idx is None:
            raise JasError("Item " + _cp_str(cp) + " not in the class")
        return _short(idx)

    def set_version(self, version_high, version_low):
        self.version_hi = version_high
        self.version_lo = version_low


class Method(object):
    def __init__(self, macc, name, desc):
        self.acc = macc
        self.name = name
        self.desc = desc
        self.sig = None
        self.code = None
        self.excepts = None
        self.depr = None
        self.ann_vis = self.ann_invis = None
        self.ann_param_vis = self.ann_param_invis = None
        self.ann_def = None
        self.generic = []

    def set_code(self, code, excepts):
        self.code = code
        self.excepts = excepts

    def set_signature(self, sig):
        self.sig = sig

    def set_deprecated(self, depr):
        self.depr = depr

    def add_generic_attr(self, g):
        self.generic.append(g)

    def add_annotation(self, visible, clsname):
        ann = Annotation.named(clsname)
        aa = self.ann_vis if visible else self.ann_invis
        if aa is None:
            aa = AnnotationAttr(visible)
            if visible:
                self.ann_vis = aa
            else:
                self.ann_invis = aa
        aa.add(ann)
        return ann

    def add_param_annotation(self, visible, clsname, paramnum):
        if paramnum <= 0 or paramnum >= 256:
            raise JasError("annotation parameter number can be in range "
                           "1-256")
        ann = Annotation.named(clsname)
        aa = self.ann_param_vis if visible else self.ann_param_invis
        if aa is None:
            aa = AnnotParamAttr(visible)
            if visible:
                self.ann_param_vis = aa
            else:
                self.ann_param_invis = aa
        aa.add(ann, paramnum - 1)
        return ann

    def add_default_annotation(self):
        if self.ann_def is not None:
            parser_error()
        self.ann_def = AnnotDefAttr()
        return self.ann_def.get()

    def _attributes(self):
        return [a for a in (self.code, self.excepts, self.sig, self.depr,
                            self.ann_vis, self.ann_invis, self.ann_param_vis,
                            self.ann_param_invis, self.ann_def)
                if a is not None]

    def resolve(self, env):
        env.add_cp_item(self.name)
        env.add_cp_item(self.desc)
        for a in self._attributes():
            a.resolve(env)
        for g in self.generic:
            g.resolve(env)

    def write(self, env, out):
        attrs = self._attributes()
        out.write_short(self.acc)
        out.write_short(env.get_cp_index(self.name))
        out.write_short(env.get_cp_index(self.desc))
        out.write_short(len(attrs) + len(self.generic))
        for a in attrs:
            a.write(env, out)
        for g in self.generic:
            g.write(env, out)


class Var(object):
    """A field."""

    def __init__(self, vacc, name, desc, cattr):
        self.var_acc = vacc
        self.name = name
        self.desc = desc
        self.const_attr = cattr
        self.sig = None
        self.depr = None
        self.ann_vis = self.ann_invis = None
        self.generic = []

    def set_signature(self, sig):
        self.sig = sig

    def set_deprecated(self, depr):
        self.depr = depr

    def add_generic_attr(self, g):
        self.generic.append(g)

    def add_annotation(self, visible, clsname):
        ann = Annotation.named(clsname)
        aa = self.ann_vis if visible else self.ann_invis
        if aa is None:
            aa = AnnotationAttr(visible)
            if visible:
                self.ann_vis = aa
            else:
                self.ann_invis = aa
        aa.add(ann)
        return ann

    def _attributes(self):
        return [a for a in (self.const_attr, self.sig, self.depr,
                            self.ann_vis, self.ann_invis)
                if a is not None]

    def resolve(self, env):
        env.add_cp_item(self.name)
        env.add_cp_item(self.desc)
        for a in self._attributes():
            a.resolve(env)
        for g in self.generic:
            g.resolve(env)

    def write(self, env, out):
        attrs = self._attributes()
        out.write_short(self.var_acc)
        out.write_short(env.get_cp_index(self.name))
        out.write_short(env.get_cp_index(self.desc))
        out.write_short(len(attrs) + len(self.generic))
        for a in attrs:
            a.write(env, out)
        for g in self.generic:
            g.write(env, out)
