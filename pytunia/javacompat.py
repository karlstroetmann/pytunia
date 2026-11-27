"""
Helpers that emulate the parts of the Java platform Jasmin relies on.

The original Jasmin is written in Java.  Several details of its output
depend on Java library behaviour, so a faithful port has to emulate them:

* Strings are sequences of UTF-16 code units.  Internally this port
  represents a Java string as a Python ``str`` whose characters are all
  <= U+FFFF (characters outside the BMP are split into surrogate pairs).
* The constant pool is stored in a ``java.util.Hashtable`` keyed by
  strings, and is written out in the Hashtable's enumeration order.  To
  produce byte-identical class files we emulate ``String.hashCode`` and
  the bucket layout of ``java.util.Hashtable``.
* Numbers carry their Java type (Integer, Long, Float, Double) because
  Jasmin's semantics depend on it.
* ``DataOutputStream`` semantics (big endian, truncation, modified UTF-8).
* The Java number parsing and formatting routines.
"""

import math
import re
import struct
import unicodedata


# ---------------------------------------------------------------------------
# Java exceptions
# ---------------------------------------------------------------------------

class JavaException(Exception):
    """An exception that the Java implementation would have raised.

    ``java_class`` is the fully qualified name of the Java exception
    class and ``message`` is the value of ``getMessage()`` (``None``
    corresponds to Java's ``null``).
    """

    def __init__(self, java_class, message=None):
        Exception.__init__(self, message)
        self.java_class = java_class
        self.message = message

    def get_message(self):
        return "null" if self.message is None else self.message

    def __str__(self):
        # corresponds to Throwable.toString()
        if self.message is None:
            return self.java_class
        return self.java_class + ": " + self.message


def number_format_error(s):
    return JavaException("java.lang.NumberFormatException",
                         'For input string: "%s"' % s)


def null_pointer():
    return JavaException("java.lang.NullPointerException", None)


def index_error(index):
    return JavaException("java.lang.StringIndexOutOfBoundsException",
                         "String index out of range: %d" % index)


# ---------------------------------------------------------------------------
# Java strings
# ---------------------------------------------------------------------------

def to_java_string(s):
    """Convert a Python string into a Java string (UTF-16 code units)."""
    if not s or max(s) <= '\uffff':
        return s
    data = s.encode('utf-16-be', 'surrogatepass')
    units = struct.unpack('>%dH' % (len(data) // 2), data)
    return ''.join(map(chr, units))


def from_java_string(s):
    """Convert a Java string into a Python string (surrogate pairs are
    combined, lone surrogates are kept)."""
    if not s:
        return s
    data = s.encode('utf-16-be', 'surrogatepass')
    return data.decode('utf-16-be', 'surrogatepass')


def printable(s):
    """Convert a Java string to a Python string that can always be
    encoded (lone surrogates become '?', as Java's encoders do)."""
    s = from_java_string(s)
    return s.encode('utf-8', 'replace').decode('utf-8')


def string_hash(s):
    """java.lang.String.hashCode()"""
    h = 0
    for c in s:
        h = (31 * h + ord(c)) & 0xFFFFFFFF
    if h & 0x80000000:
        h -= 0x100000000
    return h


def substring(s, begin, end=None):
    """java.lang.String.substring with Java's bounds checking."""
    if end is None:
        end = len(s)
        if begin < 0:
            raise index_error(begin)
        if end - begin < 0:
            raise index_error(end - begin)
        return s[begin:]
    if begin < 0:
        raise index_error(begin)
    if end > len(s):
        raise index_error(end)
    if end - begin < 0:
        raise index_error(end - begin)
    return s[begin:end]


def char_at(s, index):
    """java.lang.String.charAt with Java's bounds checking."""
    if index < 0 or index >= len(s):
        raise index_error(index)
    return s[index]


def modified_utf8(s):
    """Encode a Java string the way DataOutputStream.writeUTF does
    (without the two length bytes)."""
    try:
        data = s.encode('ascii')
        if '\x00' not in s:
            if len(data) > 65535:
                raise JavaException("java.io.UTFDataFormatException",
                                    "encoded string too long: %d bytes"
                                    % len(data))
            return data
    except UnicodeEncodeError:
        pass
    # For BMP characters UTF-8 with 'surrogatepass' is identical to
    # modified UTF-8, except for the encoding of U+0000.
    data = s.encode('utf-8', 'surrogatepass').replace(b'\x00', b'\xc0\x80')
    if len(data) > 65535:
        raise JavaException("java.io.UTFDataFormatException",
                            "encoded string too long: %d bytes" % len(data))
    return data


# ---------------------------------------------------------------------------
# java.util.Hashtable (enumeration order emulation)
# ---------------------------------------------------------------------------

class JavaHashtable(object):
    """A map with string keys that enumerates its entries in exactly the
    same order as java.util.Hashtable (JDK 1.2 - 21) does."""

    _MAX_ARRAY_SIZE = 0x7FFFFFFF - 8

    def __init__(self, capacity=11, load_factor=0.75):
        if capacity == 0:
            capacity = 1
        self._load_factor = load_factor
        # every bucket is a list of [key, value, hash]; index 0 is the
        # head of the chain
        self._table = [None] * capacity
        self._threshold = int(min(capacity * load_factor,
                                  self._MAX_ARRAY_SIZE + 1))
        self._count = 0
        self._map = {}

    def __len__(self):
        return self._count

    def __contains__(self, key):
        return key in self._map

    def get(self, key, default=None):
        entry = self._map.get(key)
        return default if entry is None else entry[1]

    def put(self, key, value):
        entry = self._map.get(key)
        if entry is not None:
            old = entry[1]
            entry[1] = value
            return old
        if self._count >= self._threshold:
            self._rehash()
        h = string_hash(key)
        tab = self._table
        index = (h & 0x7FFFFFFF) % len(tab)
        entry = [key, value, h]
        if tab[index] is None:
            tab[index] = [entry]
        else:
            tab[index].insert(0, entry)
        self._map[key] = entry
        self._count += 1
        return None

    def _rehash(self):
        old = self._table
        new_capacity = (len(old) << 1) + 1
        new = [None] * new_capacity
        self._threshold = int(min(new_capacity * self._load_factor,
                                  self._MAX_ARRAY_SIZE + 1))
        for i in range(len(old) - 1, -1, -1):
            chain = old[i]
            if chain is None:
                continue
            for entry in chain:
                index = (entry[2] & 0x7FFFFFFF) % new_capacity
                if new[index] is None:
                    new[index] = [entry]
                else:
                    new[index].insert(0, entry)
        self._table = new

    def _entries(self):
        tab = self._table
        for i in range(len(tab) - 1, -1, -1):
            chain = tab[i]
            if chain is not None:
                for entry in chain:
                    yield entry

    def keys(self):
        return [e[0] for e in self._entries()]

    def values(self):
        """Values in the order of Hashtable.elements()."""
        return [e[1] for e in self._entries()]

    def items(self):
        return [(e[0], e[1]) for e in self._entries()]


# ---------------------------------------------------------------------------
# Java numbers
# ---------------------------------------------------------------------------

class JavaInteger(int):
    """A java.lang.Integer"""
    java_type = "Integer"

    def __new__(cls, value):
        value = int(value) & 0xFFFFFFFF
        if value & 0x80000000:
            value -= 0x100000000
        return int.__new__(cls, value)

    def to_java_string(self):
        return str(int(self))


class JavaLong(int):
    """A java.lang.Long"""
    java_type = "Long"

    def __new__(cls, value):
        value = int(value) & 0xFFFFFFFFFFFFFFFF
        if value & 0x8000000000000000:
            value -= 0x10000000000000000
        return int.__new__(cls, value)

    def to_java_string(self):
        return str(int(self))


class JavaFloat(float):
    """A java.lang.Float (the value is rounded to single precision)"""
    java_type = "Float"

    def __new__(cls, value):
        return float.__new__(cls, to_float32(value))

    def to_java_string(self):
        return float_to_string(self)


class JavaDouble(float):
    """A java.lang.Double"""
    java_type = "Double"

    def __new__(cls, value):
        return float.__new__(cls, float(value))

    def to_java_string(self):
        return double_to_string(self)


def int_value(n):
    """Number.intValue()"""
    if isinstance(n, float):
        return d2i(n)
    return int(JavaInteger(n))


def long_value(n):
    """Number.longValue()"""
    if isinstance(n, float):
        return d2l(n)
    return int(n)


def float_value(n):
    """Number.floatValue()"""
    return to_float32(float(n)) if not isinstance(n, int) else \
        _long_to_float32(int(n))


def double_value(n):
    """Number.doubleValue()"""
    return float(n)


def _long_to_float32(v):
    # Java's long -> float conversion rounds once (round half even)
    if v == 0:
        return 0.0
    neg = v < 0
    a = -v if neg else v
    nbits = a.bit_length()
    if nbits > 24:
        shift = nbits - 24
        mant = a >> shift
        rest = a - (mant << shift)
        half = 1 << (shift - 1)
        if rest > half or (rest == half and (mant & 1)):
            mant += 1
        a = mant << shift
    f = float(a)
    return -f if neg else f


_FLOAT32 = struct.Struct('>f')
_DOUBLE = struct.Struct('>d')
_FLOAT_MAX = 3.4028234663852886e+38      # Float.MAX_VALUE
_FLOAT_MIN = 1.401298464324817e-45       # Float.MIN_VALUE


def to_float32(x):
    """Round a Python float (double) to single precision ((float) cast)."""
    x = float(x)
    if x != x:
        return x
    try:
        return _FLOAT32.unpack(_FLOAT32.pack(x))[0]
    except OverflowError:
        return math.copysign(math.inf, x)


def d2i(x):
    """(int) cast of a double"""
    if x != x:
        return 0
    if x >= 2147483647:
        return 2147483647
    if x <= -2147483648:
        return -2147483648
    return int(x)


def d2l(x):
    """(long) cast of a double"""
    if x != x:
        return 0
    if x >= 9223372036854775807:
        return 9223372036854775807
    if x <= -9223372036854775808:
        return -9223372036854775808
    return int(x)


# --- number parsing --------------------------------------------------------

def java_digit(ch, radix):
    """Character.digit(ch, radix)"""
    if isinstance(ch, int):
        if ch < 0:
            return -1
        ch = chr(ch)
    o = ord(ch)
    if 48 <= o <= 57:
        d = o - 48
    elif 97 <= o <= 122:
        d = o - 87
    elif 65 <= o <= 90:
        d = o - 55
    elif 0xFF21 <= o <= 0xFF3A:          # fullwidth Latin capital letters
        d = o - 0xFF21 + 10
    elif 0xFF41 <= o <= 0xFF5A:          # fullwidth Latin small letters
        d = o - 0xFF41 + 10
    elif o > 127 and unicodedata.category(ch) == 'Nd':
        d = unicodedata.decimal(ch, -1)
    else:
        return -1
    return d if d < radix else -1


def _parse_integral(s, radix, min_value, max_value):
    if s is None:
        raise JavaException("java.lang.NumberFormatException", "null")
    if not s:
        raise number_format_error(s)
    i = 0
    negative = False
    if s[0] < '0':
        if s[0] == '-':
            negative = True
        elif s[0] != '+':
            raise number_format_error(s)
        if len(s) == 1:
            raise number_format_error(s)
        i = 1
    result = 0
    for ch in s[i:]:
        d = java_digit(ch, radix)
        if d < 0:
            raise number_format_error(s)
        result = result * radix + d
        if result > max_value + 1:
            raise number_format_error(s)
    if negative:
        result = -result
    if result < min_value or result > max_value:
        raise number_format_error(s)
    return result


def parse_int(s, radix=10):
    """Integer.parseInt"""
    return _parse_integral(s, radix, -0x80000000, 0x7FFFFFFF)


def parse_long(s, radix=10):
    """Long.parseLong"""
    return _parse_integral(s, radix, -0x8000000000000000,
                           0x7FFFFFFFFFFFFFFF)


def parse_short(s, radix=10):
    """Short.parseShort"""
    i = parse_int(s, radix)
    if i < -32768 or i > 32767:
        raise JavaException("java.lang.NumberFormatException",
                            'Value out of range. Value:"%s" Radix:%d'
                            % (s, radix))
    return i


_DECIMAL_RE = re.compile(
    r'[+-]?(?:NaN|Infinity|'
    r'(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?[fFdD]?)\Z')
_HEX_RE = re.compile(
    r'([+-])?0[xX]((?:[0-9a-fA-F]+\.?)|(?:[0-9a-fA-F]*\.[0-9a-fA-F]+))'
    r'[pP]([+-]?[0-9]+)[fFdD]?\Z')


def _java_trim(s):
    start, end = 0, len(s)
    while start < end and s[start] <= ' ':
        start += 1
    while end > start and s[end - 1] <= ' ':
        end -= 1
    return s[start:end]


def parse_double(s):
    """Double.parseDouble (new Double(String))"""
    t = _java_trim(s)
    m = _HEX_RE.match(t)
    if m:
        sign, mant, exp = m.group(1), m.group(2), m.group(3)
        value = float.fromhex('0x' + mant + 'p' + exp)
        return -value if sign == '-' else value
    if not _DECIMAL_RE.match(t):
        raise number_format_error(s)
    if t[-1] in 'fFdD':
        t = t[:-1]
    if t.endswith('NaN'):
        return math.nan
    if t.endswith('Infinity'):
        return -math.inf if t[0] == '-' else math.inf
    return float(t)


# --- number formatting -----------------------------------------------------
#
# Float.toString and Double.toString of JDK 8 (sun.misc.FloatingDecimal).
# The algorithm does not always produce the shortest representation, so
# it is ported here as is.  (The strings matter: they are part of the keys
# that determine the order of the constant pool.)

_N_5_BITS = [0] + [(5 ** i).bit_length() for i in range(1, 27)]
_LONG_5_POW = [5 ** i for i in range(27)]
_SMALL_5_POW = _LONG_5_POW[:14]
_INSIGNIFICANT_DIGITS = [
    0, 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 3,
    4, 4, 4, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7,
    8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 11, 11, 11,
    12, 12, 12, 12, 13, 13, 13, 14, 14, 14,
    15, 15, 15, 15, 16, 16, 16, 17, 17, 17,
    18, 18, 18, 19]
_EXP_SHIFT = 52
_FRACT_HOB = 1 << _EXP_SHIFT
_SIGNIF_MASK = _FRACT_HOB - 1
_MAX_SMALL_BIN_EXP = 62
_MIN_SMALL_BIN_EXP = -(63 // 3)


def _wrap32(v):
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v


def _wrap64(v):
    v &= 0xFFFFFFFFFFFFFFFF
    return v - 0x10000000000000000 if v & 0x8000000000000000 else v


def _insignificant_digits_for_pow2(p2):
    if 1 < p2 < len(_INSIGNIFICANT_DIGITS):
        return _INSIGNIFICANT_DIGITS[p2]
    return 0


def _estimate_dec_exp(fract_bits, bin_exp):
    d2 = _DOUBLE.unpack(struct.pack('>Q', 0x3FF0000000000000 |
                                    (fract_bits & _SIGNIF_MASK)))[0]
    d = (d2 - 1.5) * 0.289529654 + 0.176091259 + float(bin_exp) * \
        0.301029995663981
    return math.floor(d)


def _develop_long_digits(dec_exponent, lvalue, insignificant):
    if insignificant != 0:
        # discard non-significant low-order bits, while rounding
        pow10 = 10 ** insignificant
        residue = lvalue % pow10
        lvalue //= pow10
        dec_exponent += insignificant
        if residue >= (pow10 >> 1):
            lvalue += 1
    s = str(lvalue)
    stripped = s.rstrip('0')
    dec_exponent += len(s) - len(stripped)
    return [ord(c) - 48 for c in stripped], dec_exponent + len(stripped)


def _dtoa(bin_exp, fract_bits, n_significant_bits, compat=True):
    """FloatingDecimal.BinaryToASCIIBuffer.dtoa: returns the digits and
    the decimal exponent (value = 0.d1d2d3... * 10**exponent)."""
    tail_zeros = (fract_bits & -fract_bits).bit_length() - 1
    # number of significant bits to the right of the point
    n_fract_bits = _EXP_SHIFT + 1 - tail_zeros
    n_tiny_bits = max(0, n_fract_bits - bin_exp - 1)
    if _MIN_SMALL_BIN_EXP <= bin_exp <= _MAX_SMALL_BIN_EXP:
        # the easy case: an integer that fits into a long
        if (n_tiny_bits < len(_LONG_5_POW) and
                n_fract_bits + _N_5_BITS[n_tiny_bits] < 64 and
                n_tiny_bits == 0):
            if bin_exp > n_significant_bits:
                insignificant = _insignificant_digits_for_pow2(
                    bin_exp - n_significant_bits - 1)
            else:
                insignificant = 0
            if bin_exp >= _EXP_SHIFT:
                fract_bits <<= bin_exp - _EXP_SHIFT
            else:
                fract_bits >>= _EXP_SHIFT - bin_exp
            return _develop_long_digits(0, fract_bits, insignificant)

    # the hard case
    dec_exp = _estimate_dec_exp(fract_bits, bin_exp)
    b5 = max(0, -dec_exp)
    b2 = b5 + n_tiny_bits + bin_exp
    s5 = max(0, dec_exp)
    s2 = s5 + n_tiny_bits
    m5 = b5
    m2 = b2 - n_significant_bits

    fract_bits >>= tail_zeros
    b2 -= n_fract_bits - 1
    common2factor = min(b2, s2)
    b2 -= common2factor
    s2 -= common2factor
    m2 -= common2factor
    # for exact powers of two, the next smallest number is only half as
    # far away as we think
    if n_fract_bits == 1:
        m2 -= 1
    if m2 < 0:
        b2 -= m2
        s2 -= m2
        m2 = 0

    digits = []
    bbits = n_fract_bits + b2 + (_N_5_BITS[b5] if b5 < len(_N_5_BITS)
                                 else b5 * 3)
    ten_s_bits = s2 + 1 + (_N_5_BITS[s5 + 1] if s5 + 1 < len(_N_5_BITS)
                           else (s5 + 1) * 3)
    if bbits < 64 and ten_s_bits < 64:
        # int (32 bit) or long (64 bit) arithmetic
        if bbits < 32 and ten_s_bits < 32:
            wrap, pow5 = _wrap32, _SMALL_5_POW
            fract = _wrap32(fract_bits)
        else:
            wrap, pow5 = _wrap64, _LONG_5_POW
            fract = fract_bits
        b = wrap(wrap(fract * pow5[b5]) << b2)
        s = wrap(pow5[s5] << s2)
        m = wrap(pow5[m5] << m2)
        tens = wrap(s * 10)
        q = b // s
        b = wrap(10 * (b % s))
        m = wrap(m * 10)
        low = b < m
        high = wrap(b + m) > tens
        if q == 0 and not high:
            dec_exp -= 1
        else:
            digits.append(q)
        if not compat or dec_exp < -3 or dec_exp >= 8:
            high = low = False
        while not low and not high:
            q = b // s
            b = wrap(10 * (b % s))
            m = wrap(m * 10)
            if m > 0:
                low = b < m
                high = wrap(b + m) > tens
            else:
                # m overflowed
                low = high = True
            digits.append(q)
        low_digit_difference = wrap(wrap(b << 1) - tens)
    else:
        # big integer arithmetic
        sval = (5 ** s5) << s2
        bval = (fract_bits * 5 ** b5) << b2
        mval = (5 ** (m5 + 1)) << (m2 + 1)
        ten_sval = (5 ** (s5 + 1)) << (s2 + 1)
        q, bval = divmod(bval, sval)
        bval *= 10
        low = bval < mval
        high = bval + mval >= ten_sval
        if q == 0 and not high:
            dec_exp -= 1
        else:
            digits.append(q)
        if not compat or dec_exp < -3 or dec_exp >= 8:
            high = low = False
        while not low and not high:
            q, bval = divmod(bval, sval)
            bval *= 10
            mval *= 10
            low = bval < mval
            high = bval + mval >= ten_sval
            digits.append(q)
        if high and low:
            bval <<= 1
            low_digit_difference = (bval > ten_sval) - (bval < ten_sval)
        else:
            low_digit_difference = 0

    dec_exponent = dec_exp + 1
    # the last digit gets rounded based on the stopping condition
    if high:
        if low:
            if low_digit_difference == 0:
                # it's a tie: choose based on which digits we like
                if digits[-1] & 1:
                    dec_exponent = _roundup(digits, dec_exponent)
            elif low_digit_difference > 0:
                dec_exponent = _roundup(digits, dec_exponent)
        else:
            dec_exponent = _roundup(digits, dec_exponent)
    return digits, dec_exponent


def _roundup(digits, dec_exponent):
    i = len(digits) - 1
    q = digits[i]
    if q == 9:
        while q == 9 and i > 0:
            digits[i] = 0
            i -= 1
            q = digits[i]
        if q == 9:
            # carryout! High-order 1, rest 0s, larger exp.
            digits[0] = 1
            return dec_exponent + 1
    digits[i] = q + 1
    return dec_exponent


def _java_format(digits, dec_exp):
    """BinaryToASCIIBuffer.getChars"""
    digits = ''.join(chr(48 + d) for d in digits)
    n = len(digits)
    if 0 < dec_exp < 8:
        k = min(n, dec_exp)
        out = digits[:k]
        if k < dec_exp:
            out += '0' * (dec_exp - k) + '.0'
        else:
            out += '.' + (digits[k:] if k < n else '0')
        return out
    if -3 < dec_exp <= 0:
        return '0.' + '0' * (-dec_exp) + digits
    out = digits[0] + '.' + (digits[1:] if n > 1 else '0') + 'E'
    if dec_exp <= 0:
        out += '-' + str(-dec_exp + 1)
    else:
        out += str(dec_exp - 1)
    return out


def double_to_string(x):
    """Double.toString(double)"""
    bits = struct.unpack('>Q', struct.pack('>d', float(x)))[0]
    negative = bits >> 63 != 0
    fract_bits = bits & _SIGNIF_MASK
    bin_exp = (bits >> _EXP_SHIFT) & 0x7FF
    if bin_exp == 0x7FF:
        if fract_bits == 0:
            return "-Infinity" if negative else "Infinity"
        return "NaN"
    if bin_exp == 0:
        if fract_bits == 0:
            return "-0.0" if negative else "0.0"
        leading_zeros = 64 - fract_bits.bit_length()
        shift = leading_zeros - (63 - _EXP_SHIFT)
        fract_bits <<= shift
        bin_exp = 1 - shift
        n_significant_bits = 64 - leading_zeros
    else:
        fract_bits |= _FRACT_HOB
        n_significant_bits = _EXP_SHIFT + 1
    bin_exp -= 1023
    digits, dec_exp = _dtoa(bin_exp, fract_bits, n_significant_bits)
    return ('-' if negative else '') + _java_format(digits, dec_exp)


def float_to_string(x):
    """Float.toString(float)"""
    bits = struct.unpack('>I', _FLOAT32.pack(to_float32(x)))[0]
    negative = bits >> 31 != 0
    fract_bits = bits & 0x7FFFFF
    bin_exp = (bits >> 23) & 0xFF
    if bin_exp == 0xFF:
        if fract_bits == 0:
            return "-Infinity" if negative else "Infinity"
        return "NaN"
    if bin_exp == 0:
        if fract_bits == 0:
            return "-0.0" if negative else "0.0"
        leading_zeros = 32 - fract_bits.bit_length()
        shift = leading_zeros - (31 - 23)
        fract_bits <<= shift
        bin_exp = 1 - shift
        n_significant_bits = 32 - leading_zeros
    else:
        fract_bits |= 1 << 23
        n_significant_bits = 24
    bin_exp -= 127
    digits, dec_exp = _dtoa(bin_exp, fract_bits << (_EXP_SHIFT - 23),
                            n_significant_bits)
    return ('-' if negative else '') + _java_format(digits, dec_exp)


def number_to_string(n):
    """Number.toString() for one of the Java number classes above."""
    return n.to_java_string()


# ---------------------------------------------------------------------------
# java.io.DataOutputStream
# ---------------------------------------------------------------------------

class DataOutput(object):
    """An in-memory DataOutputStream."""

    def __init__(self):
        self.buf = bytearray()

    def write_byte(self, v):
        self.buf.append(v & 0xFF)

    def write_short(self, v):
        v &= 0xFFFF
        self.buf.append(v >> 8)
        self.buf.append(v & 0xFF)

    def write_int(self, v):
        self.buf += (v & 0xFFFFFFFF).to_bytes(4, 'big')

    def write_long(self, v):
        self.buf += (v & 0xFFFFFFFFFFFFFFFF).to_bytes(8, 'big')

    def write_float(self, v):
        if v != v:
            self.buf += b'\x7f\xc0\x00\x00'      # Float.floatToIntBits(NaN)
        else:
            self.buf += _FLOAT32.pack(v)

    def write_double(self, v):
        if v != v:
            self.buf += b'\x7f\xf8\x00\x00\x00\x00\x00\x00'
        else:
            self.buf += _DOUBLE.pack(v)

    def write_utf(self, s):
        data = modified_utf8(s)
        self.write_short(len(data))
        self.buf += data

    def write(self, data):
        self.buf += data

    def size(self):
        return len(self.buf)

    def getvalue(self):
        return bytes(self.buf)
