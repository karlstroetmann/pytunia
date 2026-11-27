"""
Instructions and their operands (port of jas.Insn, jas.InsnOperand,
jas.Label, jas.LabelOrOffset and the special instruction classes).
"""

from . import constants as rc
from .errors import JasError


def _short(v):
    """(short) cast"""
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


# ---------------------------------------------------------------------------
# operands
# ---------------------------------------------------------------------------

class InsnOperand(object):
    def write(self, env, ce, out):
        raise NotImplementedError

    def size(self, env, ce):
        raise NotImplementedError

    def resolve(self, env):
        return

    def write_prefix(self, env, ce, out):
        return


class LabelOperand(InsnOperand):
    def __init__(self, target, source, wide, line):
        self.target = target
        self.source = source
        self.wide = wide
        self.ref = line

    def size(self, env, ce):
        return 4 if self.wide else 2

    def write(self, env, ce, out):
        if self.wide:
            self.target.write_wide_offset(ce, self.source, out)
        else:
            offset = ce.get_pc(self.target)
            if self.source is not None:
                offset -= ce.get_pc(self.source)
            if offset > 32767 or offset < -32768:
                raise JasError("reference from line %d exceed size for short"
                               % self.ref)
            self.target.write_offset(ce, self.source, out)


class UnsignedByteOperand(InsnOperand):
    def __init__(self, n):
        self.val = n

    def size(self, env, ce):
        return 1

    def write(self, env, ce, out):
        if self.val >= 256:
            raise JasError("Operand is too large (%d) for this instruction"
                           % self.val)
        out.write_byte(self.val)


class UnsignedByteWideOperand(InsnOperand):
    def __init__(self, n, wide):
        self.val = n
        self.wide = wide or n > 255

    def size(self, env, ce):
        return 3 if self.wide else 1

    def write_prefix(self, env, ce, out):
        if self.wide:
            out.write_byte(rc.OPC_WIDE)

    def write(self, env, ce, out):
        if self.wide:
            out.write_short(self.val)
        else:
            out.write_byte(self.val)


class ByteOperand(InsnOperand):
    def __init__(self, n):
        self.val = n

    def size(self, env, ce):
        return 1

    def write(self, env, ce, out):
        out.write_byte(self.val)


class IntegerOperand(InsnOperand):
    def __init__(self, n):
        self.val = n

    def size(self, env, ce):
        return 4

    def write(self, env, ce, out):
        out.write_int(self.val)


class ShortOperand(InsnOperand):
    def __init__(self, n):
        self.offset = n

    def size(self, env, ce):
        return 2

    def write(self, env, ce, out):
        out.write_short(self.offset)


class CPOperand(InsnOperand):
    def __init__(self, cpe, wide=True):
        self.cpe = cpe
        self.wide = wide

    def size(self, env, ce):
        return 2 if self.wide else 1

    def resolve(self, env):
        env.add_cp_item(self.cpe)

    def write(self, env, ce, out):
        idx = env.get_cp_index(self.cpe)
        if self.wide:
            out.write_short(idx)
        else:
            if idx > 255:
                raise JasError("exceeded size for small cpidx" +
                               _cp_str(self.cpe))
            out.write_byte(idx)


def _cp_str(cpe):
    # Only AsciiCP defines toString() in the Java version; for the other
    # classes Java prints "<class>@<hash>", which is not reproducible.
    if type(cpe).__name__ == 'AsciiCP':
        return str(cpe)
    return 'jas.' + type(cpe).__name__


class LdcOperand(InsnOperand):
    def __init__(self, source, cpe, wide=True):
        self.source = source
        self.cpe = cpe
        self.wide = wide

    def size(self, env, ce):
        if self.wide:
            return 2
        idx = env.get_cp_index(self.cpe)
        if idx > 255:
            # automatically switch to ldc_w
            self.wide = True
            self.source.opc = rc.OPC_LDC_W
            return 2
        return 1

    def resolve(self, env):
        env.add_cp_item(self.cpe)

    def write(self, env, ce, out):
        idx = env.get_cp_index(self.cpe)
        if self.wide:
            out.write_short(idx)
        else:
            if idx > 255:
                raise JasError("exceeded size for small cpidx" +
                               _cp_str(self.cpe))
            out.write_byte(idx)


class InvokeinterfaceOperand(InsnOperand):
    def __init__(self, cpe, nargs):
        self.cpe = cpe
        self.nargs = nargs

    def size(self, env, ce):
        return 4

    def resolve(self, env):
        env.add_cp_item(self.cpe)

    def write(self, env, ce, out):
        out.write_short(env.get_cp_index(self.cpe))
        out.write_byte(self.nargs)
        out.write_byte(0)


class IincOperand(InsnOperand):
    def __init__(self, vindex, constt, wide):
        self.vindex = vindex
        self.constt = constt
        # NB: "constt < 127" (instead of "constt < -128") is a bug of the
        # original implementation, kept here for compatibility: every iinc
        # whose increment is not 127 gets a wide prefix.
        self.wide = (wide or vindex > 255 or constt > 127 or constt < 127)

    def size(self, env, ce):
        return 5 if self.wide else 2

    def write_prefix(self, env, ce, out):
        if self.wide:
            out.write_byte(rc.OPC_WIDE)

    def write(self, env, ce, out):
        if self.wide:
            out.write_short(self.vindex)
            out.write_short(self.constt)
        else:
            out.write_byte(self.vindex)
            out.write_byte(self.constt)


class MultiarrayOperand(InsnOperand):
    def __init__(self, cpe, sz):
        self.cpe = cpe
        self.sz = sz

    def resolve(self, env):
        env.add_cp_item(self.cpe)

    def size(self, env, ce):
        return 3

    def write(self, env, ce, out):
        out.write_short(env.get_cp_index(self.cpe))
        out.write_byte(self.sz)


def _padding(source_pc):
    if (source_pc + 1) % 4 != 0:
        return 4 - ((source_pc + 1) % 4)
    return 0


class LookupswitchOperand(InsnOperand):
    def __init__(self, source, default, match, jmp):
        self.dflt = default
        self.jmp = jmp
        self.match = match
        self.source = source

    def size(self, env, ce):
        sz = 8                      # 4 + 4 + padding + jumptable
        sz += _padding(ce.get_pc(self.source))
        if self.jmp is not None:
            sz += 8 * len(self.jmp)
        return sz

    def write(self, env, ce, out):
        for _ in range(_padding(ce.get_pc(self.source))):
            out.write_byte(0)
        self.dflt.write_wide_offset(ce, self.source, out)
        if self.jmp is None:
            out.write_int(0)
        else:
            out.write_int(len(self.jmp))
            for m, j in zip(self.match, self.jmp):
                out.write_int(m)
                j.write_wide_offset(ce, self.source, out)


class TableswitchOperand(InsnOperand):
    def __init__(self, source, min_, max_, default, jmp):
        self.min = min_
        self.max = max_
        self.dflt = default
        self.jmp = jmp
        self.source = source

    def size(self, env, ce):
        sz = 12                     # 4 + 4 + 4 + jumptable + padding
        sz += _padding(ce.get_pc(self.source))
        if self.jmp is not None:
            sz += 4 * len(self.jmp)
        return sz

    def write(self, env, ce, out):
        for _ in range(_padding(ce.get_pc(self.source))):
            out.write_byte(0)
        self.dflt.write_wide_offset(ce, self.source, out)
        out.write_int(self.min)
        out.write_int(self.max)
        for j in self.jmp:
            j.write_wide_offset(ce, self.source, out)


class OffsetOperand(InsnOperand):
    """A branch offset given as a number."""

    def __init__(self, parent, val, wide=False):
        self.parent = parent
        self.val = val
        self.wide = wide

    def size(self, env, ce):
        return 4 if self.wide else 2

    def write(self, env, ce, out):
        if self.wide:
            out.write_int(self.val)
        else:
            out.write_short(self.val)


RelativeOffsetOperand = OffsetOperand


# ---------------------------------------------------------------------------
# instructions
# ---------------------------------------------------------------------------

_BRANCHES = frozenset([
    rc.OPC_GOTO, rc.OPC_IF_ACMPEQ, rc.OPC_IF_ACMPNE, rc.OPC_IF_ICMPEQ,
    rc.OPC_IF_ICMPGE, rc.OPC_IF_ICMPGT, rc.OPC_IF_ICMPLE, rc.OPC_IF_ICMPLT,
    rc.OPC_IF_ICMPNE, rc.OPC_IFEQ, rc.OPC_IFGE, rc.OPC_IFGT, rc.OPC_IFLE,
    rc.OPC_IFLT, rc.OPC_IFNE, rc.OPC_IFNONNULL, rc.OPC_IFNULL, rc.OPC_JSR])

_WIDE_BRANCHES = frozenset([rc.OPC_GOTO_W, rc.OPC_JSR_W])

_LOCAL_VAR_INSNS = frozenset([
    rc.OPC_RET, rc.OPC_ILOAD, rc.OPC_LLOAD, rc.OPC_FLOAD, rc.OPC_DLOAD,
    rc.OPC_ALOAD, rc.OPC_ISTORE, rc.OPC_LSTORE, rc.OPC_FSTORE,
    rc.OPC_DSTORE, rc.OPC_ASTORE])

_CP_INSNS = frozenset([
    rc.OPC_ANEWARRAY, rc.OPC_INVOKEDYNAMIC, rc.OPC_INVOKENONVIRTUAL,
    rc.OPC_INVOKESTATIC, rc.OPC_INVOKEVIRTUAL, rc.OPC_NEW, rc.OPC_CHECKCAST,
    rc.OPC_INSTANCEOF, rc.OPC_GETSTATIC, rc.OPC_PUTSTATIC, rc.OPC_GETFIELD,
    rc.OPC_PUTFIELD])


class Insn(object):
    """A JVM instruction.  Use the factory methods to create one."""

    def __init__(self, opc=None, operand=None):
        self.opc = opc
        self.operand = operand

    @classmethod
    def simple(cls, opc):
        """Instructions without arguments."""
        if rc.OPC_LENGTHS[opc] == 1:
            return cls(opc)
        raise JasError(rc.OPC_NAMES[opc] +
                       " cannot be used without more parameters")

    @staticmethod
    def _check_short(val, opc):
        if val > 32767 or val < -32768:
            raise JasError(rc.OPC_NAMES[opc] +
                           " numeric value exceed size for short")

    @classmethod
    def with_int(cls, opc, val, wide):
        """Instructions taking a single numeric argument (including
        branches whose target is given as an offset)."""
        insn = cls(opc)
        if opc == rc.OPC_BIPUSH:
            if val > 127 or val < -128:
                raise JasError("bipush value exceed size of byte")
            insn.operand = ByteOperand(val)
        elif opc == rc.OPC_SIPUSH or opc in _BRANCHES:
            cls._check_short(val, opc)
            insn.operand = OffsetOperand(insn, val)
        elif opc in _WIDE_BRANCHES:
            insn.operand = OffsetOperand(insn, val, True)
        elif opc == rc.OPC_NEWARRAY:
            if val < 0 or val > 255:
                raise JasError("newarray counter is illegal")
            insn.operand = UnsignedByteOperand(val)
        elif opc in _LOCAL_VAR_INSNS:
            insn.operand = UnsignedByteWideOperand(val, wide)
        else:
            raise JasError(rc.OPC_NAMES[opc] +
                           " does not take a numeric argument")
        return insn

    @classmethod
    def with_relative(cls, opc, val):
        """Branches with a relative numeric target."""
        insn = cls(opc)
        if opc in _BRANCHES:
            cls._check_short(val, opc)
            insn.operand = RelativeOffsetOperand(insn, val)
        elif opc in _WIDE_BRANCHES:
            insn.operand = RelativeOffsetOperand(insn, val, True)
        else:
            raise JasError(rc.OPC_NAMES[opc] +
                           " does not take a relative numeric argument")
        return insn

    @classmethod
    def with_label(cls, opc, target, line):
        """Instructions taking a label as argument."""
        insn = cls(opc)
        if opc in _BRANCHES:
            insn.operand = LabelOperand(target, insn, False, line)
        elif opc in _WIDE_BRANCHES:
            insn.operand = LabelOperand(target, insn, True, line)
        else:
            raise JasError(rc.OPC_NAMES[opc] +
                           " does not take a label as its argument")
        return insn

    @classmethod
    def with_cp(cls, opc, arg):
        """Instructions taking a constant pool entry as argument."""
        insn = cls(opc)
        if opc in _CP_INSNS:
            insn.operand = CPOperand(arg)
        elif opc == rc.OPC_LDC2_W or opc == rc.OPC_LDC_W:
            insn.operand = LdcOperand(insn, arg)
        elif opc == rc.OPC_LDC:
            insn.operand = LdcOperand(insn, arg, False)
        else:
            raise JasError(rc.OPC_NAMES[opc] +
                           " does not take a CP item as an argument")
        return insn

    def resolve(self, env):
        if self.operand is not None:
            self.operand.resolve(env)

    def write(self, env, ce, out):
        if self.operand is not None:
            self.operand.write_prefix(env, ce, out)
        out.write_byte(self.opc)
        if self.operand is not None:
            self.operand.write(env, ce, out)

    def size(self, env, ce):
        if self.operand is None:
            return 1
        return 1 + self.operand.size(env, ce)

    def __str__(self):
        return "instruction %d %s" % (self.opc, "" if self.operand is None
                                      else self.operand.__class__.__name__)


class Label(Insn):
    """A label in the code.  Labels with the same name are identical."""

    def __init__(self, tag):
        Insn.__init__(self, rc.OPC_LABEL)
        self.id = tag

    def write(self, env, ce, out):
        return

    def size(self, env, ce):
        return 0

    def write_offset(self, ce, source, out):
        """write the offset (as a short)"""
        pc = ce.get_pc(self)
        tpc = 0 if source is None else ce.get_pc(source)
        out.write_short(pc - tpc)

    def write_wide_offset(self, ce, source, out):
        pc = ce.get_pc(self)
        tpc = 0 if source is None else ce.get_pc(source)
        out.write_int(pc - tpc)

    def get_offset(self, ce):
        return _short(ce.get_pc(self))

    def __str__(self):
        return "Label: " + self.id


class LabelOrOffset(object):
    """A branch target given either as a label or as a numeric offset."""

    def __init__(self, label=None, offset=0):
        self.label = label
        self.offset = offset

    def write_wide_offset(self, ce, source, out):
        if self.label is not None:
            self.label.write_wide_offset(ce, source, out)
        else:
            out.write_int(self.offset)


def IincInsn(vindex, increment, wide):
    return Insn(rc.OPC_IINC, IincOperand(vindex, increment, wide))


def InvokeinterfaceInsn(cpe, nargs):
    return Insn(rc.OPC_INVOKEINTERFACE, InvokeinterfaceOperand(cpe, nargs))


def MultiarrayInsn(cpe, sz):
    return Insn(rc.OPC_MULTIANEWARRAY, MultiarrayOperand(cpe, sz))


def TableswitchInsn(min_, max_, default, jmp):
    insn = Insn(rc.OPC_TABLESWITCH)
    insn.operand = TableswitchOperand(insn, min_, max_, default, jmp)
    return insn


def LookupswitchInsn(default, match, target):
    insn = Insn(rc.OPC_LOOKUPSWITCH)
    insn.operand = LookupswitchOperand(insn, default, match, target)
    return insn
