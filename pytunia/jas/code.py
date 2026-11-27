"""
The Code attribute and the tables that belong to it (port of
jas.CodeAttr, jas.Catchtable, jas.CatchEntry, jas.LineTableAttr,
jas.LocalVarEntry, jas.LocalVarTableAttr and jas.LocalVarTypeTableAttr).
"""

from .cp import AsciiCP
from .errors import JasError
from .insn import Label


class CodeAttr(object):
    attr = AsciiCP("Code")

    def __init__(self):
        self.stack_size = 1
        self.num_locals = 1
        self.ctb = None
        self.ltab = None
        self.lvar = None
        self.lvtyp = None
        self.stackmap = None
        self.insns = []
        self.insn_pc = None
        self.generic = []

    def set_catchtable(self, ctb):
        self.ctb = ctb

    def set_line_table(self, ltab):
        self.ltab = ltab

    def set_local_var_table(self, lvar):
        self.lvar = lvar

    def set_local_var_type_table(self, lvtyp):
        self.lvtyp = lvtyp

    def set_stack_map(self, stackmap):
        self.stackmap = stackmap

    def add_generic_attr(self, g):
        self.generic.append(g)

    def add_insn(self, insn):
        self.insns.append(insn)

    def set_stack_size(self, stack_size):
        self.stack_size = stack_size

    def set_var_size(self, num_vars):
        self.num_locals = num_vars

    def resolve(self, env):
        env.add_cp_item(self.attr)
        for insn in self.insns:
            insn.resolve(env)
        if self.ctb is not None:
            self.ctb.resolve(env)
        if self.ltab is not None:
            self.ltab.resolve(env)
        if self.lvar is not None:
            self.lvar.resolve(env)
        if self.lvtyp is not None:
            self.lvtyp.resolve(env)
        if self.stackmap is not None:
            self.stackmap.resolve(env)
        for g in self.generic:
            g.resolve(env)

    def get_pc(self, insn):
        if self.insn_pc is None:
            raise JasError("Internal error, insn_pc has not been initialized")
        if isinstance(insn, Label):
            pc = self.insn_pc.get(insn.id)
        else:
            pc = self.insn_pc.get(insn)
        if pc is None:
            raise JasError(str(insn) + " has not been added to the code")
        return pc

    def write(self, env, out):
        # First, resolve all labels and compute the total size
        code_size = 0
        self.insn_pc = insn_pc = {}
        for now in self.insns:
            if isinstance(now, Label):
                insn_pc[now.id] = code_size
            else:
                insn_pc[now] = code_size
            code_size += now.size(env, self)

        total_size = code_size
        if self.ctb is not None:
            total_size += self.ctb.size()
        if self.ltab is not None:
            total_size += self.ltab.size()
        if self.lvar is not None:
            total_size += self.lvar.size()
        if self.lvtyp is not None:
            total_size += self.lvtyp.size()
        if self.stackmap is not None:
            total_size += self.stackmap.size(env, self)
        for g in self.generic:
            total_size += g.size()
        total_size += 12            # extra headers

        out.write_short(env.get_cp_index(self.attr))
        out.write_int(total_size)
        out.write_short(self.stack_size)
        out.write_short(self.num_locals)
        out.write_int(code_size)
        for now in self.insns:
            now.write(env, self, out)

        if self.ctb is not None:
            self.ctb.write(env, self, out)
        else:
            out.write_short(0)

        extra = 0
        if self.ltab is not None:
            extra += 1
        if self.lvar is not None:
            extra += 1
        if self.lvtyp is not None:
            extra += 1
        if self.stackmap is not None:
            extra += 1
        extra += len(self.generic)
        out.write_short(extra)

        if self.ltab is not None:
            self.ltab.write(env, self, out)
        if self.lvar is not None:
            self.lvar.write(env, self, out)
        if self.lvtyp is not None:
            self.lvtyp.write(env, self, out)
        if self.stackmap is not None:
            self.stackmap.write(env, self, out)
        for g in self.generic:
            g.write(env, out)

    def __str__(self):
        return "<#code-attr>"


class CatchEntry(object):
    def __init__(self, start, end, handler, cat):
        """start/end/handler are either all Labels or all ints"""
        if isinstance(start, Label):
            self.start_pc, self.end_pc, self.handler_pc = start, end, handler
            self.start_off = self.end_off = self.handler_off = 0
        else:
            self.start_pc = self.end_pc = self.handler_pc = None
            self.start_off, self.end_off, self.handler_off = \
                start, end, handler
        self.catch_cpe = cat

    def resolve(self, env):
        if self.catch_cpe is not None:
            env.add_cp_item(self.catch_cpe)

    def write(self, env, ce, out):
        if (self.start_pc is not None and self.end_pc is not None and
                self.handler_pc is not None):
            self.start_pc.write_offset(ce, None, out)
            self.end_pc.write_offset(ce, None, out)
            self.handler_pc.write_offset(ce, None, out)
        else:
            out.write_short(self.start_off)
            out.write_short(self.end_off)
            out.write_short(self.handler_off)
        if self.catch_cpe is not None:
            out.write_short(env.get_cp_index(self.catch_cpe))
        else:
            out.write_short(0)


class Catchtable(object):
    def __init__(self):
        self.entries = []

    def add_entry(self, start, end, handler, cat):
        self.entries.append(CatchEntry(start, end, handler, cat))

    def resolve(self, env):
        for entry in self.entries:
            entry.resolve(env)

    def size(self):
        return 8 * len(self.entries)     # each entry is 8 bytes

    def write(self, env, ce, out):
        out.write_short(len(self.entries))
        for entry in self.entries:
            entry.write(env, ce, out)


class LineTableAttr(object):
    attr = AsciiCP("LineNumberTable")

    def __init__(self):
        self.line = []
        self.pc = []

    def add_entry(self, label, line):
        self.pc.append(label)
        self.line.append(line)

    def resolve(self, env):
        env.add_cp_item(self.attr)

    def size(self):
        return 2 + 4 + 2 + 4 * len(self.pc)

    def write(self, env, ce, out):
        out.write_short(env.get_cp_index(self.attr))
        out.write_int(2 + 4 * len(self.pc))
        out.write_short(len(self.pc))
        for label, line in zip(self.pc, self.line):
            label.write_offset(ce, None, out)
            out.write_short(line)


class LocalVarEntry(object):
    def __init__(self, start, end, name, sig, slot):
        """start/end are either Labels or int offsets"""
        if isinstance(start, Label) or start is None:
            self.start, self.end = start, end
            self.starto = self.endo = 0
        else:
            self.start = self.end = None
            self.starto, self.endo = start, end
        self.name = AsciiCP(name)
        self.sig = AsciiCP(sig)
        self.slot = slot

    def resolve(self, env):
        env.add_cp_item(self.name)
        env.add_cp_item(self.sig)

    def write(self, env, ce, out):
        if self.start is not None and self.end is not None:
            self.start.write_offset(ce, None, out)
            self.end.write_offset(ce, self.start, out)   # the *length*
        else:
            out.write_short(self.starto)
            out.write_short(self.endo - self.starto)
        out.write_short(env.get_cp_index(self.name))
        out.write_short(env.get_cp_index(self.sig))
        out.write_short(self.slot)


class LocalVarTableAttr(object):
    attr = AsciiCP("LocalVariableTable")

    def __init__(self):
        self.vars = []

    def add_entry(self, entry):
        self.vars.append(entry)

    def resolve(self, env):
        env.add_cp_item(self.attr)
        for lv in self.vars:
            lv.resolve(env)

    def size(self):
        return 2 + 4 + 2 + 10 * len(self.vars)

    def write(self, env, ce, out):
        out.write_short(env.get_cp_index(self.attr))
        out.write_int(2 + 10 * len(self.vars))
        out.write_short(len(self.vars))
        for lv in self.vars:
            lv.write(env, ce, out)


class LocalVarTypeTableAttr(LocalVarTableAttr):
    attr = AsciiCP("LocalVariableTypeTable")
