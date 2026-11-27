"""
Translates the abstract syntax tree of a Jasmin file into calls of the
methods of ClassFile, which build the class.

The tree is the nested tuple that Larkita builds from the grammar jasmin.g
(see "How the abstract syntax tree is built" in Larkita's documentation).
Tokens appear in it as pairs such as ("WORD", "java/lang/Object") or
("INT", 42); an ("EOL", n) pair ends every line, and n is the number of the
line where the statement started.

The methods of ClassFile are called in the same order and with the same
arguments as by the semantic actions of Jasmin's parser (parser.cup), so
that the class files are identical to those of Jasmin.
"""

from .jas import constants as rc
from .javacompat import JavaInteger
from .scanner import convert_dots, split_method_signature


_ACCESS_FLAGS = {
    "public": rc.ACC_PUBLIC, "private": rc.ACC_PRIVATE,
    "protected": rc.ACC_PROTECTED, "static": rc.ACC_STATIC,
    "final": rc.ACC_FINAL, "synchronized": rc.ACC_SYNCHRONIZED,
    "volatile": rc.ACC_VOLATILE, "transient": rc.ACC_TRANSIENT,
    "native": rc.ACC_NATIVE, "interface": rc.ACC_INTERFACE,
    "abstract": rc.ACC_ABSTRACT, "annotation": rc.ACC_ANNOTATION,
    "enum": rc.ACC_ENUM, "bridge": rc.ACC_BRIDGE,
    "varargs": rc.ACC_VARARGS, "fpstrict": rc.ACC_STRICT,
    "synthetic": rc.ACC_SYNTHETIC,
}


def _access(node):
    """The access flags of a node like ("access", "public", "static")."""
    flags = 0
    for name in node[1:]:
        flags |= _ACCESS_FLAGS[name]
    return flags


def _short(v):
    """The value of v as a Java short."""
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def _item(token):
    """The value of an item: INT values become JavaIntegers."""
    kind, value = token
    return JavaInteger(value) if kind == "INT" else value


def _optional(node):
    """The value of the token in an optional part of a rule, e.g. "x" for
    ("signature", ("STR", "x")), or None for ("signature",)."""
    return node[-1][1] if len(node) > 1 else None


def _optional_class(node):
    name = _optional(node)
    return None if name is None else convert_dots(name)


def _line(node):
    """The line where the construct ``node`` starts: the value of its first
    EOL token (or None if it has none)."""
    for child in node[1:]:
        if isinstance(child, tuple):
            if child[0] == "EOL":
                return child[1]
            line = _line(child)
            if line is not None:
                return line
    return None


class Translator(object):
    def __init__(self, class_file):
        self.cf = class_file

    def translate(self, tree):
        """Translates the tree of a jas_file."""
        _, header, *items = tree
        self.header(header)
        for item in items:
            self.cf.set_line(_line(item))
            match item[0]:
                case ".inner":
                    self.inner_class(item)
                case ".field" | ".field block":
                    self.field(item)
                case ".method":
                    self.method(item)

    # ------------------------------------------------------------------
    # the class header
    # ------------------------------------------------------------------

    def header(self, node):
        cf = self.cf
        for item in node[1:]:
            cf.set_line(_line(item))
            match item:
                case (".bytecode", ("NUM", version), _):
                    cf.set_version(version)
                case (".source", (_, name), _):
                    cf.set_source(name)
                case (".class", access, ("WORD", name), _):
                    cf.set_class(convert_dots(name),
                                 _short(_access(access) | rc.ACC_SUPER))
                case (".interface", access, ("WORD", name), _):
                    cf.set_class(convert_dots(name),
                                 _short(_access(access) | rc.ACC_SUPER |
                                        rc.ACC_INTERFACE))
                case (".super", ("WORD", name), _):
                    cf.set_super_class(convert_dots(name))
                case (".implements", ("WORD", name), _):
                    cf.add_interface(convert_dots(name))
                case (".enclosing", ("WORD", method), _):
                    cf.set_enclosing_method(method)
                case (".debug", ("STR", extension), _):
                    cf.set_source_debug_extension(extension)
                case _:
                    self.attribute(item)
        cf.end_header()

    def attribute(self, node):
        """The directives that may appear in the class header, in fields
        and in methods (ClassFile decides where they belong)."""
        cf = self.cf
        match node:
            case (".signature", ("STR", signature), *_):
                cf.set_signature(signature)
            case (".deprecated", *_):
                cf.set_deprecated()
            case (".attribute", ("WORD", name), ("STR", file_name), *_):
                cf.add_generic_attr(name, file_name)
            case (".annotation", visibility, ("WORD", type_), ("EOL", _),
                  *fields):
                cf.add_annotation(visibility == "visible", convert_dots(type_))
                self.annotation_fields(fields)
                cf.end_annotation()
            case (".annotation param", visibility, ("INT", parameter),
                  ("WORD", type_), ("EOL", _), *fields):
                cf.add_param_annotation(visibility == "visibleparam",
                                        convert_dots(type_), parameter)
                self.annotation_fields(fields)
                cf.end_annotation()
            case (".annotation default", ("EOL", _), ("WORD", descriptor),
                  *sub_type, values):
                cf.add_default_annotation()
                cf.add_annotation_field(None, descriptor,
                                        sub_type[0][1] if sub_type else None)
                self.annotation_values(values)
                cf.end_annotation()

    # ------------------------------------------------------------------
    # annotations
    # ------------------------------------------------------------------

    def annotation_fields(self, fields):
        cf = self.cf
        for field in fields:
            if field[0] == "EOL":
                continue        # the end of the line with .end annotation
            cf.set_line(_line(field))
            match field:
                case ("=", ("WORD", name), ("WORD", descriptor),
                      ("WORD", sub_type), values):
                    cf.add_annotation_field(name, descriptor, sub_type)
                    self.annotation_values(values)
                case ("=", ("WORD", name), ("WORD", descriptor), values):
                    cf.add_annotation_field(name, descriptor, None)
                    self.annotation_values(values)

    def annotation_values(self, node):
        cf = self.cf
        for value in node[1:]:
            match value:
                case ("nested annotation", ("EOL", _), *fields):
                    cf.nest_annotation()
                    self.annotation_fields(fields)
                    cf.end_annotation()
                case ("EOL", _):
                    pass
                case _:
                    cf.add_annotation_value(_item(value))

    # ------------------------------------------------------------------
    # inner classes and fields
    # ------------------------------------------------------------------

    def inner_class(self, node):
        _, kind, access, name, inner, outer, _ = node
        flags = _access(access)
        if kind == "interface":
            flags |= rc.ACC_INTERFACE
        self.cf.add_inner(_short(flags), _optional(name),
                          _optional_class(inner), _optional_class(outer))

    def field(self, node):
        cf = self.cf
        match node:
            case (".field", access, ("WORD", name), ("WORD", descriptor),
                  ("signature", ("STR", signature)), value, _):
                cf.add_field(_short(_access(access)), name, descriptor,
                             signature, self.field_value(value))
            case (".field", access, ("WORD", name), ("WORD", descriptor),
                  value, _):
                cf.add_field(_short(_access(access)), name, descriptor, None,
                             self.field_value(value))
            case (".field block", ("field_start", access, ("WORD", name),
                                   ("WORD", descriptor), value, _),
                  *attributes, ("EOL", end_line)):
                cf.begin_field(_short(_access(access)), name, descriptor,
                               self.field_value(value))
                for attribute in attributes:
                    cf.set_line(_line(attribute))
                    self.attribute(attribute)
                cf.set_line(end_line)
                cf.end_field()

    @staticmethod
    def field_value(node):
        """The initial value of a field: ("=", item) or ("=",)"""
        return _item(node[1]) if len(node) > 1 else None

    # ------------------------------------------------------------------
    # methods
    # ------------------------------------------------------------------

    def method(self, node):
        cf = self.cf
        _, access, (_, signature), _, *statements, (_, end_line) = node
        name, descriptor = split_method_signature(signature)
        cf.new_method(name, descriptor, _access(access))
        for statement in statements:
            cf.set_line(_line(statement))
            match statement:
                case ("statement", ("EOL", _)):
                    pass                        # an empty statement
                case ("statement", body, _):
                    self.statement(body)
        cf.set_line(end_line)
        cf.end_method()

    def statement(self, node):
        cf = self.cf
        match node:
            case (":", ("WORD", label)):
                cf.plant_label(label)
            case (":", ("INT", label), instruction):
                # (Jasmin plants the label after the instruction; ClassFile
                # puts numeric labels in front of it)
                self.instruction(instruction)
                cf.plant_label(str(label))
            case ("instruction" | "lookupswitch" | "tableswitch", *_):
                self.instruction(node)
            case _:
                self.directive(node)

    # ------------------------------------------------------------------
    # instructions
    # ------------------------------------------------------------------

    def instruction(self, node):
        cf = self.cf
        match node:
            case ("instruction", ("INSN", name)):
                cf.plant(name)
            case ("instruction", ("INSN", name), ("INT", n)):
                cf.plant_int(name, n)
            case ("instruction", ("INSN", name), ("INT", n1), ("INT", n2)):
                cf.plant_int_int(name, n1, n2)
            case ("instruction", ("INSN", name), ("NUM", number)):
                cf.plant_num(name, number)
            case ("instruction", ("INSN", name), ("WORD", word)):
                cf.plant_word(name, word)
            case ("instruction", ("INSN", name), ("WORD", word), ("INT", n)):
                cf.plant_word_int(name, word, n)
            case ("instruction", ("INSN", name), ("WORD", word1),
                  ("WORD", word2)):
                cf.plant_word_word(name, word1, word2)
            case ("instruction", ("INSN", name), ("STR", string)):
                cf.plant_string(name, string)
            case ("instruction", ("INSN", name), ("RELATIVE", offset)):
                cf.plant_relative_goto(name, offset)
            case ("lookupswitch", ("EOL", _), *entries, default):
                self.lookupswitch(entries, default)
            case ("tableswitch", ("INT", low), ("INT", high), ("EOL", _),
                  *entries, default):
                cf.new_tableswitch(low, high)
                self.tableswitch(entries, default)
            case ("tableswitch", ("INT", low), ("EOL", _), *entries,
                  default):
                cf.new_tableswitch(low)
                self.tableswitch(entries, default)

    def lookupswitch(self, entries, default):
        cf = self.cf
        cf.new_lookupswitch()
        for entry in entries:
            match entry:
                case (":", ("INT", key), ("WORD", label), _):
                    cf.add_lookupswitch(key, label)
                case (":", ("INT", key), ("INT", offset), _):
                    cf.add_lookupswitch_offset(key, offset)
        match default:
            case ("WORD", label):
                cf.end_lookupswitch(label)
            case ("INT", offset):
                cf.end_lookupswitch_offset(offset)

    def tableswitch(self, entries, default):
        cf = self.cf
        for entry in entries:
            match entry:
                case ("table_entry", ("WORD", label), _):
                    cf.add_tableswitch(label)
                case ("table_entry", ("INT", offset), _):
                    cf.add_tableswitch_offset(offset)
        match default:
            case ("WORD", label):
                cf.end_tableswitch(label)
            case ("INT", offset):
                cf.end_tableswitch_offset(offset)

    # ------------------------------------------------------------------
    # directives in methods
    # ------------------------------------------------------------------

    def directive(self, node):
        cf = self.cf
        match node:
            case (".var", ("INT", register), ("WORD", name),
                  ("WORD", descriptor), signature):
                cf.add_var(None, None, name, descriptor, _optional(signature),
                           register)
            case (".var", ("INT", register), ("WORD", name),
                  ("WORD", descriptor), signature, ("WORD", start),
                  ("WORD", end)):
                cf.add_var(start, end, name, descriptor, _optional(signature),
                           register)
            case (".var", ("INT", register), ("WORD", name),
                  ("WORD", descriptor), signature, ("INT", start),
                  ("INT", end)):
                cf.add_var_offsets(start, end, name, descriptor,
                                   _optional(signature), register)
            case ((".limit", "locals"), ("INT", n)):
                cf.set_var_size(n)
            case ((".limit", "stack"), ("INT", n)):
                cf.set_stack_size(n)
            case (".limit", ("WORD", word), _):
                cf.report_error('.limit expected "stack" or "locals", but got '
                                + word)
            case (".line", ("INT", line)):
                cf.add_line(line)
            case (".throws", ("WORD", name)):
                cf.add_throw(convert_dots(name))
            case (".catch", ("WORD", name), ("WORD", start), ("WORD", end),
                  ("WORD", handler)):
                cf.add_catch(convert_dots(name), start, end, handler)
            case (".catch", ("WORD", name), ("INT", start), ("INT", end),
                  ("INT", handler)):
                cf.add_catch_offsets(convert_dots(name), start, end, handler)
            case (".set", *_):
                pass    # variables are rejected by the scanner
            case (".stack", ("EOL", _), offset, *items):
                cf.begin_stack(False)
                self.stack_frame(offset, items)
            case (".stack use", ("INT", n), ("EOL", _), offset, *items):
                cf.begin_stack_n(n)
                self.stack_frame(offset, items)
            case (".stack use", ("EOL", _), offset, *items):
                cf.begin_stack(True)
                self.stack_frame(offset, items)
            case _:
                self.attribute(node)

    def stack_frame(self, offset, items):
        cf = self.cf
        match offset:
            case ("offset", ("INT", n), _):
                cf.plant_stack_offset(n)
            case ("offset", ("WORD", label), _):
                cf.plant_stack_offset_label(label)
        for item in items:
            match item:
                case (kind, ("WORD", type_), ("EOL", _)):
                    value = None
                case (kind, ("WORD", type_), ("WORD", value), _):
                    pass
                case (kind, ("WORD", type_), ("INT", n), _):
                    value = str(n)
            if kind == "locals":
                cf.plant_stack_locals(type_, value)
            else:
                cf.plant_stack_stack(type_, value)
        cf.end_stack()
