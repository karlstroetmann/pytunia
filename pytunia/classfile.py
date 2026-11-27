"""
The ClassFile class: uses the parser and the jas package to create Java
class files (port of jasmin.ClassFile).

read_jasmin() parses the source (scanner.py, parser.py) and hands the
abstract syntax tree to translator.py, which calls the methods of
ClassFile that build the class (set_class, new_method, plant, ...).

A ClassFile object represents the binary data that makes up a Java class
file.  This is the low-level interface of the assembler, with the same
methods as the Java version (most programs will use pytunia.assemble() or
pytunia.assemble_string() instead)::

    from pytunia import ClassFile

    cf = ClassFile()
    with open("HelloWorld.j", encoding="utf-8", newline="") as f:
        cf.read_jasmin(f, "HelloWorld.j", False)
    if cf.error_count() == 0:
        with open("HelloWorld.class", "wb") as out:
            cf.write(out)
    else:
        for diagnostic in cf.diagnostics:
            print(diagnostic)
"""

from . import insninfo
from .jas import (JasError, ClassEnv, ClassCP, StringCP, IntegerCP, FloatCP,
                  LongCP, DoubleCP, AsciiCP, ConstAttr, Var, Method,
                  MethodCP, FieldCP, InterfaceCP, SignatureAttr,
                  DeprecatedAttr, GenericAttr, CodeAttr, Catchtable,
                  LocalVarTableAttr, LocalVarTypeTableAttr, LocalVarEntry,
                  LineTableAttr, ExceptAttr, Insn, Label, LabelOrOffset,
                  IincInsn, InvokeinterfaceInsn, MultiarrayInsn,
                  TableswitchInsn, LookupswitchInsn, StackMap, VerifyFrame)
from .diagnostics import Diagnostic
from .jas.annotation import parser_error
from .javacompat import (JavaException, JavaInteger, JavaLong, JavaFloat,
                         JavaDouble, DataOutput, number_to_string,
                         parse_int, parse_short, substring, int_value,
                         long_value, float_value, double_value,
                         to_java_string, from_java_string, printable)
from .parser import UnexpectedToken, parse, syntax_error_message
from .javatypes import class_operand, field_descriptor
from .scanner import (Scanner, split_class_method_signature,
                      split_class_field)
from .translator import Translator


def _int32(v):
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v


def _opened_annotation(fld):
    raise JasError("Skipped .end annotation in " + fld)


def _outside(directive):
    raise JasError("illegal use of " + directive +
                   " outside of method/field definition or class header")


def _annotation_internal():
    raise JasError("logic error in .annotation parsing")


def _is_number(name):
    try:
        parse_int(name)
        return True
    except JavaException:
        return False


_ARRAY_TYPES = {"boolean": 4, "char": 5, "float": 6, "double": 7,
                "byte": 8, "short": 9, "int": 10, "long": 11}


class ClassFile(object):
    BGN_METHOD = "jasmin_reserved_bgnmethod:"
    END_METHOD = "jasmin_reserved_endmethod:"

    def __init__(self, err=None):
        """Error messages are collected in the list ``diagnostics``.  If
        ``err`` is a stream, they are also written to it (the command line
        interface passes sys.stderr)."""
        self.err = err
        self.diagnostics = []
        self.source_given = False
        # state info for the class being built
        self.filename = None
        self.class_env = None
        self.class_name = None
        self.source_name = None
        self.source_lines = []
        # the scanner while the source is parsed (for error messages)
        self.scanner = None
        # state info for the current method being defined
        self.except_attr = None
        self.catch_table = None
        self.var_table = None
        self.vtype_table = None
        self.line_table = None
        self.code = None
        self.cur_method = None
        self.cur_field = None
        self.labels = None
        self.stackmap = None
        self.verifyframe = None
        self.cur_annotation = None
        self.line_label_count = 0
        # the line of the statement that is translated (for line number
        # tables and error messages)
        self.line_num = None
        self.stack_map_label_count = 0
        self._auto_number = False
        self.class_header = False
        self.buffered_insn = None
        # state info for lookupswitch and tableswitch instructions
        self.switch_vec = None
        self.low_value = 0
        self.high_value = 0
        # number of errors reported in a file
        self.errors = 0

    # ------------------------------------------------------------------
    # error reporting
    # ------------------------------------------------------------------

    def report_error(self, msg, line=None, column=None):
        """Reports an error in the line ``line`` of the source, at the
        column ``column`` (both counted from 1; the column may be None).
        Without a line, the error is reported at the position of the
        scanner while the source is parsed, and at the statement that is
        translated afterwards."""
        self.errors += 1
        if line is None:
            if self.scanner is not None:
                line, column = self.scanner.error_position()
            else:
                line = self.line_num
        filename = "null" if self.filename is None else self.filename
        sentence = msg if msg.endswith(".") else msg + "."
        source_line = None
        if line is None:
            text = "%s: %s" % (filename, sentence)
        else:
            text = "%s:%d: %s" % (filename, line, sentence)
            if 0 < line <= len(self.source_lines):
                source_line = self.source_lines[line - 1].rstrip("\r")
                text += "\n" + source_line
                if column is not None:
                    # point at the column (tabs are kept, so that the
                    # caret is aligned)
                    prefix = source_line[:column - 1]
                    text += "\n" + "".join(
                        "\t" if c == "\t" else " " for c in prefix) + "^"
                    column = len(from_java_string(prefix))
                source_line = printable(source_line)
        if source_line is None:
            column = None
        text = printable(text)
        self.diagnostics.append(Diagnostic(
            printable(filename), line, printable(msg), source_line,
            column, text))
        if self.err is not None:
            self.err.write(text + "\n")
            self.err.flush()

    # ------------------------------------------------------------------
    # class header
    # ------------------------------------------------------------------

    def set_source(self, name):
        """.source directive"""
        self.source_name = name
        self.source_given = True

    def set_version(self, version):
        """.bytecode directive"""
        s = number_to_string(version)
        idx = s.find(".")
        if not isinstance(version, JavaFloat) or idx == -1:
            self.report_error("invalid bytecode version number : " + s)
        self.class_env.set_version(parse_short(substring(s, 0, idx)),
                                   parse_short(substring(s, idx + 1)))

    def set_class(self, name, acc):
        """.class directive"""
        self.class_name = name
        self.class_env.set_class(ClassCP(name))
        self.class_env.set_class_access(acc)
        self.class_header = True

    def set_super_class(self, name):
        """.super directive"""
        self.class_env.set_super_class(ClassCP(name))

    def add_interface(self, name):
        """.implements directive"""
        self.class_env.add_interface(ClassCP(name))

    def set_source_debug_extension(self, s):
        """.debug directive"""
        self.class_env.set_source_debug_extension(s)

    def set_enclosing_method(self, s):
        """.enclosing directive"""
        try:
            if "(" in s:            # full method description
                split = split_class_method_signature(s)
                self.class_env.set_enclosing_method(*split)
            else:                   # just a class name
                self.class_env.set_enclosing_method(s, None, None)
        except JavaException as e:
            if e.java_class not in ("java.lang.IllegalArgumentException",
                                    "java.lang.NumberFormatException"):
                raise
            self.report_error(str(e))

    def end_header(self):
        """called at the end of the jasmin header"""
        if self.cur_annotation is not None:
            _opened_annotation("class header")
        self.class_env.end_header()     # resolve annotations
        self.class_header = False

    def set_signature(self, s):
        """.signature directive"""
        sig = SignatureAttr(s)
        if self.cur_method is not None:
            self.cur_method.set_signature(sig)
        elif self.cur_field is not None:
            self.cur_field.set_signature(sig)
        elif self.class_header:
            self.class_env.set_signature(s)
        else:
            _outside(".signature")

    def set_deprecated(self):
        """.deprecated directive"""
        depr = DeprecatedAttr()
        if self.cur_method is not None:
            self.cur_method.set_deprecated(depr)
        elif self.cur_field is not None:
            self.cur_field.set_deprecated(depr)
        elif self.class_header:
            self.class_env.set_deprecated(depr)
        else:
            _outside(".deprecated")

    def add_generic_attr(self, name, filename):
        """.attribute directive"""
        gattr = GenericAttr.from_file(name, filename)
        if self.cur_method is not None:
            self.flush_insn_buffer()
            if self.code is not None:
                self.code.add_generic_attr(gattr)
            else:
                self.cur_method.add_generic_attr(gattr)
        elif self.cur_field is not None:
            self.cur_field.add_generic_attr(gattr)
        elif self.class_header:
            self.class_env.add_generic_attr(gattr)
        else:
            _outside(".attribute")

    def add_inner(self, iacc, name, inner, outer):
        """.inner directive"""
        self.class_env.add_inner_class(iacc, name, inner, outer)

    # ------------------------------------------------------------------
    # annotations
    # ------------------------------------------------------------------

    def add_default_annotation(self):
        """.annotation default"""
        if self.cur_method is None:
            parser_error()
        self.cur_annotation = self.cur_method.add_default_annotation()

    def add_param_annotation(self, visible, clname, paramnum):
        """.annotation visibleparam / invisibleparam"""
        if self.cur_method is None:
            parser_error()
        self.cur_annotation = self.cur_method.add_param_annotation(
            visible, clname, paramnum)

    def add_annotation(self, visible, clname):
        """.annotation visible / invisible"""
        if self.cur_method is not None:
            self.cur_annotation = self.cur_method.add_annotation(visible,
                                                                 clname)
        elif self.cur_field is not None:
            self.cur_annotation = self.cur_field.add_annotation(visible,
                                                                clname)
        elif self.class_header:
            self.cur_annotation = self.class_env.add_annotation(visible,
                                                                clname)
        else:
            _outside(".annotation")

    def add_annotation_field(self, name, type_, add):
        if self.cur_annotation is None:
            _annotation_internal()
        self.cur_annotation.add_field(name, type_, add)

    def add_annotation_value(self, value):
        if self.cur_annotation is None:
            _annotation_internal()
        self.cur_annotation.add_value(value)

    def nest_annotation(self):
        if self.cur_annotation is None:
            _annotation_internal()
        self.cur_annotation = self.cur_annotation.nest_annotation()

    def end_annotation(self):
        if self.cur_annotation is None:
            raise JasError(".end annotation without .annotation")
        self.cur_annotation = self.cur_annotation.end_annotation()

    # ------------------------------------------------------------------
    # fields
    # ------------------------------------------------------------------

    def begin_field(self, access, name, desc, value):
        """.field directive (begins a field)"""
        ca = None
        if value is not None:
            # create a constant pool entry for the initial value
            if isinstance(value, JavaInteger):
                cp = IntegerCP(int(value))
            elif isinstance(value, JavaFloat):
                cp = FloatCP(float(value))
            elif isinstance(value, JavaDouble):
                cp = DoubleCP(float(value))
            elif isinstance(value, JavaLong):
                cp = LongCP(int(value))
            elif isinstance(value, str):
                cp = StringCP(value)
            else:
                raise JasError("usupported value type")
            ca = ConstAttr(cp)
        self.cur_field = Var(access, AsciiCP(name), AsciiCP(desc), ca)

    def end_field(self):
        """.end field directive"""
        if self.cur_field is None:
            raise JasError(".end field without .field")
        if self.cur_annotation is not None:
            _opened_annotation("field")
        self.class_env.add_field(self.cur_field)
        self.cur_field = None

    def add_field(self, access, name, desc, sig, value):
        """single line .field directive"""
        self.begin_field(access, name, desc, value)
        if sig is not None:
            self.cur_field.set_signature(SignatureAttr(sig))
        self.end_field()

    # ------------------------------------------------------------------
    # methods
    # ------------------------------------------------------------------

    def new_method(self, name, descriptor, access):
        """.method directive"""
        self.labels = {}
        self.code = None
        self.except_attr = None
        self.catch_table = None
        self.var_table = None
        self.vtype_table = None
        self.line_table = None
        self.line_label_count = 0
        self.stack_map_label_count = 0
        self.stackmap = None
        self.verifyframe = None
        self.cur_method = Method(access, AsciiCP(name), AsciiCP(descriptor))

    def end_method(self):
        """.end method directive"""
        if self.cur_method is None:
            raise JasError(".end method without .method")
        if self.cur_annotation is not None:
            _opened_annotation("method")
        code = self.code
        if code is not None:
            self.plant_label(self.END_METHOD)
            self.flush_insn_buffer()
            if self.catch_table is not None:
                code.set_catchtable(self.catch_table)
            if self.var_table is not None:
                code.set_local_var_table(self.var_table)
            if self.vtype_table is not None:
                code.set_local_var_type_table(self.vtype_table)
            if self.line_table is not None:
                code.set_line_table(self.line_table)
            if self.stackmap is not None:
                code.set_stack_map(self.stackmap)
        self.cur_method.set_code(code, self.except_attr)
        self.class_env.add_method(self.cur_method)
        # clear method state variables
        self.cur_method = None
        self.code = None
        self.labels = None
        self.catch_table = None
        self.line_table = None
        self.var_table = None
        self.vtype_table = None
        self.stackmap = None
        self.verifyframe = None

    # ------------------------------------------------------------------
    # stack map frames (.stack directive)
    # ------------------------------------------------------------------

    def _prev_stack(self, count):
        """get the last stackmap locals vector"""
        if self.stackmap is not None:
            return self.stackmap.get_last_frame(count)
        return None

    def begin_stack(self, copy):
        """define a new stack map frame (possibly copying the previous)"""
        prev = None
        if copy:
            prev = self._prev_stack(0)
        self.verifyframe = VerifyFrame(prev)

    def begin_stack_n(self, n):
        """define a new stack map frame and copy n previous elements"""
        if n <= 0:
            raise JasError("Invalid counter")
        self.verifyframe = VerifyFrame(self._prev_stack(n))

    def plant_stack_offset(self, n):
        """define the offset of the current stack map frame"""
        try:
            self.verifyframe.set_offset(n)
        except JasError as e:
            self.report_error(str(e))

    def plant_stack_offset_label(self, label):
        lab = self.get_label(label)
        try:
            self.verifyframe.set_offset(lab)
        except JasError as e:
            self.report_error(str(e))

    def plant_stack_locals(self, item, val):
        """add a local variable item to the current stack map frame"""
        try:
            self.verifyframe.add_locals_item(item, val)
        except JasError as e:
            self.report_error(str(e))

    def plant_stack_stack(self, item, val):
        """add a stack item element to the current stack map frame"""
        try:
            self.verifyframe.add_stack_item(item, val)
        except JasError as e:
            self.report_error(str(e))

    def end_stack(self):
        """add the current frame to the current stack map attribute"""
        if not self.verifyframe.have_offset():
            lab = "jasmin_reserved_SM:%d" % self.stack_map_label_count
            self.stack_map_label_count += 1
            try:
                self.plant_label(lab)
                self.verifyframe.set_offset(self.get_label(lab))
            except JasError as e:
                self.report_error(str(e))
        if self.stackmap is None:
            self.stackmap = StackMap(self.class_env)
        self.stackmap.add_frame(self.verifyframe)
        self.verifyframe = None

    # ------------------------------------------------------------------
    # plant routines - these add instructions to the code of the current
    # method
    # ------------------------------------------------------------------

    def plant(self, name):
        """instructions that take no arguments"""
        insn = insninfo.get(name)
        self.auto_number()
        self.flush_insn_buffer()
        if insn.args == "":
            self.buffer_insn(Insn.simple(insn.opcode))
        else:
            raise JasError("Missing arguments for instruction " + name)

    def plant_relative_goto(self, name, val):
        """relative branch targets (ie $+5, $-12, ...)"""
        insn = insninfo.get(name)
        if insn.args == "label":
            self.buffer_insn(Insn.with_int(insn.opcode, val, True))
        else:       # forward the request for "normal" instructions
            self.plant_int(name, val)

    def plant_int_int(self, name, v1, v2):
        """iinc"""
        insn = insninfo.get(name)
        self.auto_number()
        self.flush_insn_buffer()
        if insn.args.lower() == "ii":
            self.buffer_insn(IincInsn(v1, v2, insn.args[0] == 'I'))
        else:
            raise JasError("Bad arguments for instruction " + name)

    def plant_int(self, name, val):
        """instructions that take an integer parameter (branches are part
        of this, the int is converted to a label)"""
        insn = insninfo.get(name)
        self._get_code()
        self.auto_number()
        self.flush_insn_buffer()
        args = insn.args
        if args.lower() == "i":
            self.buffer_insn(Insn.with_int(insn.opcode, val, args[0] == 'I'))
        elif args == "constant":
            self.buffer_insn(Insn.with_cp(insn.opcode, IntegerCP(val)))
        elif args == "bigconstant":
            self.buffer_insn(Insn.with_cp(insn.opcode, LongCP(val)))
        elif args == "label":
            # the target is not signed: assume it is a label
            self.plant_word(name, str(val))
        else:
            raise JasError("Bad arguments for instruction " + name)

    def plant_num(self, name, val):
        """ldc and other instructions that take a numeric argument"""
        insn = insninfo.get(name)
        self._get_code()
        self.auto_number()
        self.flush_insn_buffer()
        args = insn.args
        is_int = isinstance(val, (JavaInteger, JavaLong))
        is_float = isinstance(val, (JavaFloat, JavaDouble))
        if args.lower() == "i" and isinstance(val, JavaInteger):
            self.buffer_insn(Insn.with_int(insn.opcode, int(val),
                                           args[0] == 'I'))
        elif args == "constant":
            if is_int:
                self.buffer_insn(Insn.with_cp(insn.opcode,
                                              IntegerCP(int_value(val))))
            elif is_float:
                self.buffer_insn(Insn.with_cp(insn.opcode,
                                              FloatCP(float_value(val))))
        elif args == "bigconstant":
            if is_int:
                self.buffer_insn(Insn.with_cp(insn.opcode,
                                              LongCP(long_value(val))))
            elif is_float:
                self.buffer_insn(Insn.with_cp(insn.opcode,
                                              DoubleCP(double_value(val))))
        else:
            raise JasError("Bad arguments for instruction " + name)

    def plant_string(self, name, val):
        """ldc <quoted-string>"""
        insn = insninfo.get(name)
        self.auto_number()
        self.flush_insn_buffer()
        if insn.args == "constant":
            self.buffer_insn(Insn.with_cp(insn.opcode, StringCP(val)))
        else:
            raise JasError("Bad arguments for instruction " + name)

    def plant_word_int(self, name, val, nargs):
        """invokeinterface and multianewarray"""
        insn = insninfo.get(name)
        self._get_code()
        self.auto_number()
        self.flush_insn_buffer()
        if insn.args == "interface":
            split = split_class_method_signature(val)
            self.buffer_insn(InvokeinterfaceInsn(InterfaceCP(*split), nargs))
        elif insn.args == "marray":
            # (pytunia converts dots and Java types, Jasmin 2.4 does not)
            self.buffer_insn(MultiarrayInsn(ClassCP(class_operand(val)),
                                            nargs))
        else:
            raise JasError("Bad arguments for instruction " + name)

    def plant_word(self, name, val):
        """instructions that take a word as a parameter (e.g. branches,
        newarray, invokemethod)"""
        insn = insninfo.get(name)
        self._get_code()
        self.auto_number()
        self.flush_insn_buffer()
        args = insn.args
        if args == "method":
            split = split_class_method_signature(val)
            self.buffer_insn(Insn.with_cp(insn.opcode, MethodCP(*split)))
        elif args == "constant":
            # (pytunia converts dots and Java types, Jasmin 2.4 does not)
            self.buffer_insn(Insn.with_cp(insn.opcode,
                                          ClassCP(class_operand(val))))
        elif args == "atype":
            atype = _ARRAY_TYPES.get(val)
            if atype is None:
                raise JasError("Bad array type: " + name)
            self.buffer_insn(Insn.with_int(insn.opcode, atype, False))
        elif "label" in args:
            self.buffer_insn(Insn.with_label(insn.opcode, self.get_label(val),
                                             self.line_num))
        elif args == "class":
            # (pytunia converts dots and Java types, Jasmin 2.4 does not)
            self.buffer_insn(Insn.with_cp(insn.opcode,
                                          ClassCP(class_operand(val))))
        else:
            raise JasError("(gloups)Bad arguments for instruction " + name)

    def plant_word_word(self, name, v1, v2):
        """instructions that take a field and a signature as parameters
        (e.g. getstatic, putstatic)"""
        info = insninfo.get(name)
        self._get_code()
        self.auto_number()
        self.flush_insn_buffer()
        if info.args == "field":
            cls, fld = split_class_field(v1)
            if fld is None:
                raise JasError("can't extract field from " + v1)
            # (pytunia converts dots and Java types in the descriptor v2,
            # Jasmin 2.4 does not)
            self.buffer_insn(Insn.with_cp(info.opcode,
                                          FieldCP(cls, fld,
                                                  field_descriptor(v2))))
        else:
            raise JasError("Bad arguments for instruction " + name)

    # --- lookupswitch -------------------------------------------------

    def new_lookupswitch(self):
        self.switch_vec = []
        self.auto_number()

    def add_lookupswitch(self, val, label):
        self.switch_vec.append((val, LabelOrOffset(self.get_label(label))))

    def add_lookupswitch_offset(self, val, offset):
        self.switch_vec.append((val, LabelOrOffset(offset=offset)))

    def end_lookupswitch(self, deflabel):
        self.flush_insn_buffer()
        offsets, labels = self._check_lookupswitch()
        defl = LabelOrOffset(self.get_label(deflabel))
        self.buffer_insn(LookupswitchInsn(defl, offsets, labels))

    def end_lookupswitch_offset(self, defoffset):
        self.flush_insn_buffer()
        offsets, labels = self._check_lookupswitch()
        self.buffer_insn(LookupswitchInsn(LabelOrOffset(offset=defoffset),
                                          offsets, labels))

    def _check_lookupswitch(self):
        offsets = [v for v, _ in self.switch_vec]
        labels = [lab for _, lab in self.switch_vec]
        return offsets, labels

    # --- tableswitch --------------------------------------------------

    def new_tableswitch(self, lowval, hival=-1):
        self.switch_vec = []
        self.low_value = lowval
        self.high_value = hival
        self.auto_number()

    def add_tableswitch(self, label):
        self.switch_vec.append(LabelOrOffset(self.get_label(label)))

    def add_tableswitch_offset(self, offset):
        self.switch_vec.append(LabelOrOffset(offset=offset))

    def end_tableswitch(self, deflabel):
        self.flush_insn_buffer()
        labels = self._check_tableswitch()
        self.buffer_insn(TableswitchInsn(
            self.low_value, _int32(self.low_value + len(labels) - 1),
            LabelOrOffset(self.get_label(deflabel)), labels))

    def end_tableswitch_offset(self, defoffset):
        self.flush_insn_buffer()
        labels = self._check_tableswitch()
        self.buffer_insn(TableswitchInsn(
            self.low_value, _int32(self.low_value + len(labels) - 1),
            LabelOrOffset(offset=defoffset), labels))

    def _check_tableswitch(self):
        labels = list(self.switch_vec)
        n = len(labels)
        if (self.high_value != -1 and
                self.high_value != _int32(self.low_value + n - 1)):
            self.report_error("tableswitch - given incorrect value for <high>")
        return labels

    # ------------------------------------------------------------------
    # line numbers
    # ------------------------------------------------------------------

    def set_line(self, line):
        """Used by the translator to tell ClassFile the line number of the
        next statement (used by the auto_number mechanism and in error
        messages)."""
        self.line_num = line

    def auto_number(self):
        """If auto_number is True, output a line number table that refers
        to the lines of the Jasmin source."""
        if self._auto_number:
            self.add_line_info(self.line_num)

    def add_line_info(self, line_num):
        lab = "jasmin_reserved_L:%d" % self.line_label_count
        self.line_label_count += 1
        if self.line_table is None:
            self.line_table = LineTableAttr()
        self.plant_label(lab)
        self.line_table.add_entry(self.get_label(lab), line_num)

    def add_line(self, line_num):
        """.line directive"""
        if not self._auto_number:
            self.add_line_info(line_num)

    # ------------------------------------------------------------------
    # labels
    # ------------------------------------------------------------------

    def get_label(self, name):
        """gets the Label object for a label, creating it if it doesn't
        exist"""
        # check that we are inside of a method definition
        if self.cur_method is None:
            raise JasError("illegal use of label outside of method "
                           "definition")
        lab = self.labels.get(name)
        if lab is None:
            lab = Label(name)
            self.labels[name] = lab
        return lab

    def plant_label(self, name):
        """defines a label"""
        if _is_number(name):
            # the label is a number, we must add it *before* the buffered
            # instruction; this is the reason to use an instruction buffer
            self._get_code().add_insn(self.get_label(name))
            self.flush_insn_buffer()
        else:
            # traditional label (word), add it *after* the buffered insn
            self.flush_insn_buffer()
            self.buffer_insn(self.get_label(name))

    def buffer_insn(self, insn):
        """if there is an instruction in the buffer, add it to the code
        and put the new instruction in the buffer"""
        if insn is None:
            raise JasError("trying to buffer a null instruction")
        if self.buffered_insn is not None:
            self.flush_insn_buffer()
        self.buffered_insn = insn

    def flush_insn_buffer(self):
        """if the buffer is not empty, add the instruction to the code"""
        if self.buffered_insn is not None:
            # (_get_code() may change buffered_insn, so it must be called
            # before the argument is evaluated -- as in Java)
            code = self._get_code()
            code.add_insn(self.buffered_insn)
            self.buffered_insn = None

    # ------------------------------------------------------------------
    # other directives
    # ------------------------------------------------------------------

    def add_var(self, start_lab, end_lab, name, desc, sign, var_num):
        """.var directive (with labels)"""
        if start_lab is None:
            start_lab = self.BGN_METHOD
        if end_lab is None:
            end_lab = self.END_METHOD
        slab = self.get_label(start_lab)
        elab = self.get_label(end_lab)
        if self.var_table is None:
            self.var_table = LocalVarTableAttr()
        self.var_table.add_entry(LocalVarEntry(slab, elab, name, desc,
                                               var_num))
        if sign is not None:
            if self.vtype_table is None:
                self.vtype_table = LocalVarTypeTableAttr()
            self.vtype_table.add_entry(LocalVarEntry(slab, elab, name, sign,
                                                     var_num))

    def add_var_offsets(self, start_offset, end_offset, name, desc, sign,
                        var_num):
        """.var directive (with offsets)"""
        if self.var_table is None:
            self.var_table = LocalVarTableAttr()
        self.var_table.add_entry(LocalVarEntry(start_offset, end_offset,
                                               name, desc, var_num))
        if sign is not None:
            if self.vtype_table is None:
                self.vtype_table = LocalVarTypeTableAttr()
            self.vtype_table.add_entry(LocalVarEntry(start_offset,
                                                     end_offset, name, sign,
                                                     var_num))

    def add_throw(self, name):
        """.throws directive"""
        if self.cur_method is None:
            raise JasError("illegal use of .throw outside of method "
                           "definition")
        if self.except_attr is None:
            self.except_attr = ExceptAttr()
        self.except_attr.add_exception(ClassCP(name))

    def add_catch(self, name, start_lab, end_lab, branch_lab):
        """.catch directive (with labels)"""
        class_cp = self._check_catch(name)
        self.catch_table.add_entry(self.get_label(start_lab),
                                   self.get_label(end_lab),
                                   self.get_label(branch_lab), class_cp)

    def add_catch_offsets(self, name, start_off, end_off, branch_off):
        """.catch directive (with offsets)"""
        class_cp = self._check_catch(name)
        self.catch_table.add_entry(start_off, end_off, branch_off, class_cp)

    @staticmethod
    def check_limit(v):
        if v < 0 or v > 65535:
            raise JasError("Illegal limit value")
        return v

    def set_stack_size(self, v):
        """.limit stack"""
        self._get_code().set_stack_size(self.check_limit(v))

    def set_var_size(self, v):
        """.limit locals"""
        self._get_code().set_var_size(self.check_limit(v))

    def _check_catch(self, name):
        # check that we are inside of a method definition
        if self.cur_method is None:
            raise JasError("illegal use of .catch outside of method "
                           "definition")
        if self.catch_table is None:
            self.catch_table = Catchtable()
        if name == "all":
            return None
        return ClassCP(name)

    def _get_code(self):
        """returns the code block, creating it if it doesn't exist"""
        # check that we are inside of a method definition
        if self.cur_method is None:
            raise JasError("illegal use of instruction outside of method "
                           "definition")
        if self.code is None:
            self.code = CodeAttr()
            self.plant_label(self.BGN_METHOD)
        return self.code

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def read_jasmin(self, source, name, number_lines):
        """Parses a Jasmin file, converting it internally into a binary
        representation.

        ``source`` is the text of the file (a str) or a text file object.
        Open files with ``newline=''`` so that line ends are not
        translated.  ``name`` is the name of the file; it is used in
        error messages and as the default SourceFile attribute.  If
        ``number_lines`` is true, a line number table that refers to the
        lines of the Jasmin source is generated.

        Errors are printed to ``err`` and counted (see error_count()).
        Fatal errors raise JasError or JavaException.
        """
        # initialize variables for error reporting
        self.errors = 0
        self.diagnostics = []
        self.scanner = None
        self.line_num = None
        self.source_given = False
        self.filename = name
        self.source_name = name
        # initialize local-frame variables
        self.cur_method = None
        self.cur_field = None
        self.cur_annotation = None
        self.class_header = False
        # if number_lines is true, we output LineTableAttrs that indicate
        # what line numbers the Jasmin code falls on
        self._auto_number = bool(number_lines)
        self.class_env = ClassEnv()
        if not isinstance(source, str):
            source = source.read()
        text = to_java_string(source)
        self.source_lines = text.split("\n")
        # parse the input file
        self.scanner = Scanner(text)
        try:
            tree = parse(self.scanner)
        except UnexpectedToken as e:
            self.report_error(syntax_error_message(e), e.token.line,
                              e.token.column)
            return
        self.scanner = None
        # build the class
        Translator(self).translate(tree)
        self.line_num = None

    def error_count(self):
        """Returns the number of warnings/errors encountered while parsing
        a file (0 if everything went OK)."""
        return self.errors

    def get_class_name(self):
        """Returns the name of the class in the file (i.e. the string given
        to the .class parameter in Jasmin)."""
        return self.class_name

    def to_bytes(self):
        """Returns the binary class file.  Raises JasError or
        JavaException if something goes wrong."""
        self.class_env.set_source(self.source_name)
        out = DataOutput()
        self.class_env.write(out)
        return out.getvalue()

    def write(self, outp):
        """Writes the class file to the binary stream ``outp``."""
        outp.write(self.to_bytes())
