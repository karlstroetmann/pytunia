"""
StackMap / StackMapTable attributes (port of jas.StackMap,
jas.VerifyFrame and jas.VerificationTypeInfo).
"""

import sys

from .cp import AsciiCP, ClassCP
from .errors import JasError
from .insn import Label
from ..javacompat import DataOutput, JavaException, parse_int, printable


_JDK_SMF_MIN = 50


class StackMap(object):
    def __init__(self, env):
        # The first StackMap of a class decides (from the class file
        # version) whether StackMapTable (Java 6+) or StackMap (CLDC)
        # frames are written.  (In the Java version this state is kept in
        # static fields, which Main resets before every file.)
        if env.stackmap_attr is None:
            env.stackmap_java6 = env.version_hi >= _JDK_SMF_MIN
            env.stackmap_attr = AsciiCP("StackMapTable" if env.stackmap_java6
                                        else "StackMap")
        self.attr = env.stackmap_attr
        self.java6 = env.stackmap_java6
        self.frames = []

    def add_frame(self, frame):
        self.frames.append(frame)

    def get_last_frame(self, count):
        if not self.frames:
            return None
        return self.frames[-1].get_frame(count)

    def size(self, env, ce):
        try:
            if self.java6:
                self._shell_sort(ce)
            return self.write(env, ce, None)
        except JasError as ex:
            # The Java version prints a stack trace here and continues;
            # the same error is raised again when the attribute is written.
            sys.stderr.write("UNEXPECTED JAS ERROR\n%s\n" % printable(str(ex)))
            return 0

    def resolve(self, env):
        env.add_cp_item(self.attr)
        for f in self.frames:
            f.resolve(env)

    def write(self, env, ce, out):
        buf = DataOutput()
        buf.write_short(len(self.frames))
        prev = None
        for cur in self.frames:
            if not self.java6:
                prev = cur          # as flag
            cur.write(env, ce, buf, prev)
            prev = cur
        length = buf.size()
        if out is not None:         # else, call for size calculation
            out.write_short(env.get_cp_index(self.attr))
            out.write_int(length)
            out.write(buf.getvalue())
        return (2 + 4) + length

    def _shell_sort(self, ce):
        frames = self.frames
        n = len(frames) - 1
        if n <= 0:
            return
        g = 3
        if g > n:
            g = 1
        while True:
            i = g
            while True:
                tmp = frames[i]
                ts = tmp.get_offset(ce)
                j = i
                while j >= g:
                    jn = j - g
                    t1 = frames[jn]
                    if t1.get_offset(ce) <= ts:
                        break
                    frames[j] = t1
                    j = jn
                frames[j] = tmp
                i += 1
                if i > n:
                    break
            g //= 2
            if g <= 0:
                break


_SAME_FRAME_S0_MIN = 0
_SAME_FRAME_S0_MAX = 63
_SAME_FRAME_S1_MIN = 64         # + vi
_SAME_FRAME_S1_MAX = 127
_SAME_FRAME_S1 = 247            # + off, vi
_CHOP_FRAME_S0_MIN = 248        # + off
_SAME_FRAME_S0 = 251            # + off
_APPEND_FRAME_S0_MAX = 254
_FULL_FRAME = 255


class VerifyFrame(object):
    def __init__(self, initial_frame):
        self.stack = []
        self.locals = initial_frame if initial_frame is not None else []
        self.offset = 0
        self.off_label = None
        self.offset_defined = False

    def _define_offset(self):
        if self.offset_defined:
            raise JasError("offset already defined")
        self.offset_defined = True

    def set_offset(self, offset):
        """offset is an int or a Label"""
        self._define_offset()
        if isinstance(offset, Label):
            self.off_label = offset
        else:
            self.offset = offset

    def add_stack_item(self, item, val):
        self.stack.append(VerificationTypeInfo(item, val))

    def add_locals_item(self, item, val):
        self.locals.append(VerificationTypeInfo(item, val))

    def have_offset(self):
        return self.offset_defined

    def get_frame(self, count):
        if count > len(self.locals):
            raise JasError("Counter exceed range", True)
        result = list(self.locals)
        if count != 0:              # else -- full copy
            del result[count:]
        return result

    def get_offset(self, ce):
        if self.off_label is not None:
            self.offset = ce.get_pc(self.off_label)
            self.off_label = None   # for speed in next's request
        return self.offset

    def resolve(self, env):
        for vti in self.stack:
            vti.resolve(env)
        for vti in self.locals:
            vti.resolve(env)

    def write(self, env, ce, out, prev):
        off = self.get_offset(ce)
        stack_size = len(self.stack)
        locals_size = len(self.locals)
        if prev is not self:            # JDK >= 6
            if prev is not None:        # not first element
                prev_off = prev.get_offset(ce)
                if prev_off >= off:
                    raise JasError("Write unsorted StackMapFrame")
                off -= prev_off + 1
            if stack_size <= 1:         # else can't compact
                can_compact = True
                prev_size = 0
                if prev is None:        # first record
                    if stack_size == 0:
                        if locals_size > (_APPEND_FRAME_S0_MAX -
                                          _SAME_FRAME_S0):
                            can_compact = False
                    elif locals_size != 0:
                        can_compact = False
                else:                   # not first record
                    cmpcn = locals_size
                    prev_size = len(prev.locals)
                    delta = locals_size - prev_size
                    if stack_size == 0:
                        if delta >= 0:
                            if delta > (_APPEND_FRAME_S0_MAX -
                                        _SAME_FRAME_S0):
                                can_compact = False
                            cmpcn -= delta
                        elif delta < (_CHOP_FRAME_S0_MIN - _SAME_FRAME_S0):
                            can_compact = False
                    elif delta != 0:
                        can_compact = False
                    if can_compact:
                        cmpcn -= 1
                        while cmpcn >= 0:
                            if not self.locals[cmpcn].is_equal(
                                    env, ce, prev.locals[cmpcn]):
                                can_compact = False
                                break
                            cmpcn -= 1
                if can_compact:
                    if stack_size != 0:     # only if SAME_FRAME_S1...
                        if off <= (_SAME_FRAME_S1_MAX - _SAME_FRAME_S1_MIN):
                            out.write_byte(off + _SAME_FRAME_S1_MIN)
                        else:
                            out.write_byte(_SAME_FRAME_S1)
                            out.write_short(off)
                        self.stack[0].write(env, ce, out)
                        return
                    wrdt = locals_size - prev_size
                    if wrdt == 0 and off <= (_SAME_FRAME_S0_MAX -
                                             _SAME_FRAME_S0_MIN):
                        out.write_byte(off + _SAME_FRAME_S0_MIN)
                        return
                    out.write_byte(_SAME_FRAME_S0 + wrdt)
                    out.write_short(off)
                    while wrdt > 0:
                        wrdt -= 1
                        self.locals[prev_size].write(env, ce, out)
                        prev_size += 1
                    return
            out.write_byte(_FULL_FRAME)
        # end of StackMapFrame (JDK >= 1.6) mode
        out.write_short(off)
        out.write_short(locals_size)    # number_of_locals
        for vti in self.locals:
            vti.write(env, ce, out)
        out.write_short(stack_size)     # number_of_stack_items
        for vti in self.stack:
            vti.write(env, ce, out)


_TAGS = {"Top": 0, "Integer": 1, "Float": 2, "Long": 4, "Double": 3,
         "Null": 5, "UninitializedThis": 6}


class VerificationTypeInfo(object):
    def __init__(self, item, val=None):
        self.cls = None
        self.index = 0
        self.un_label = None
        if item in _TAGS:
            self.tag = _TAGS[item]
        elif item == "Object":
            if val is None:
                raise JasError("Object requires a class name")
            self.cls = ClassCP(val)
            self.tag = 7
        elif item == "Uninitialized":
            if val is None:
                raise JasError("Uninitialized requires an integer or label")
            try:
                self.index = parse_int(val)
            except JavaException:
                self.un_label = Label(val)
            self.tag = 8
        else:
            raise JasError("Unknown item verification type : " + item)

    def resolve(self, env):
        if self.tag == 7:
            self.cls.resolve(env)
            env.add_cp_item(self.cls)

    def write(self, env, ce, out):
        out.write_byte(self.tag)
        if self.tag == 7:
            out.write_short(env.get_cp_index(self.cls))
        elif self.tag == 8:             # Uninitialized
            if self.un_label is not None:
                self.un_label.write_offset(ce, None, out)
            else:
                if (self.index & 0xFFFF) == self.index:   # fits as a short
                    out.write_short(self.index)
                else:
                    out.write_int(self.index)

    def _get_offset(self, ce):
        if self.un_label is not None:
            return self.un_label.get_offset(ce)
        return self.index

    def is_equal(self, env, ce, cmp):
        if self.tag != cmp.tag:
            return False
        if self.tag == 7:
            return env.get_cp_index(self.cls) == env.get_cp_index(cmp.cls)
        if self.tag == 8:
            return self._get_offset(ce) == cmp._get_offset(ce)
        return True
