"""
Constants of the Java class file format (port of jas.RuntimeConstants).
"""

JAVA_MAGIC = -889275714          # 0xCAFEBABE
JAVA_VERSION = 45
JAVA_MINOR_VERSION = 3

# constant pool tags
CONSTANT_UTF8 = 1
CONSTANT_UNICODE = 2
CONSTANT_INTEGER = 3
CONSTANT_FLOAT = 4
CONSTANT_LONG = 5
CONSTANT_DOUBLE = 6
CONSTANT_CLASS = 7
CONSTANT_STRING = 8
CONSTANT_FIELD = 9
CONSTANT_METHOD = 10
CONSTANT_INTERFACEMETHOD = 11
CONSTANT_NAMEANDTYPE = 12

# access flags
ACC_PUBLIC = 0x0001
ACC_PRIVATE = 0x0002
ACC_PROTECTED = 0x0004
ACC_STATIC = 0x0008
ACC_FINAL = 0x0010
ACC_SYNCHRONIZED = 0x0020      # method
ACC_SUPER = 0x0020             # class (auto)
ACC_VOLATILE = 0x0040          # field
ACC_BRIDGE = 0x0040            # method
ACC_TRANSIENT = 0x0080         # field
ACC_VARARGS = 0x0080           # method
ACC_NATIVE = 0x0100
ACC_INTERFACE = 0x0200
ACC_ABSTRACT = 0x0400
ACC_STRICT = 0x0800
ACC_SYNTHETIC = 0x1000
ACC_ANNOTATION = 0x2000
ACC_ENUM = 0x4000

# array types for newarray
T_CLASS = 2
T_BOOLEAN = 4
T_CHAR = 5
T_FLOAT = 6
T_DOUBLE = 7
T_BYTE = 8
T_SHORT = 9
T_INT = 10
T_LONG = 11

# opcodes
OPC_TRY = -3
OPC_DEAD = -2
OPC_LABEL = -1
OPC_NOP = 0
OPC_ACONST_NULL = 1
OPC_ICONST_M1 = 2
OPC_ICONST_0 = 3
OPC_ICONST_1 = 4
OPC_ICONST_2 = 5
OPC_ICONST_3 = 6
OPC_ICONST_4 = 7
OPC_ICONST_5 = 8
OPC_LCONST_0 = 9
OPC_LCONST_1 = 10
OPC_FCONST_0 = 11
OPC_FCONST_1 = 12
OPC_FCONST_2 = 13
OPC_DCONST_0 = 14
OPC_DCONST_1 = 15
OPC_BIPUSH = 16
OPC_SIPUSH = 17
OPC_LDC = 18
OPC_LDC_W = 19
OPC_LDC2_W = 20
OPC_ILOAD = 21
OPC_LLOAD = 22
OPC_FLOAD = 23
OPC_DLOAD = 24
OPC_ALOAD = 25
OPC_ILOAD_0 = 26
OPC_ILOAD_1 = 27
OPC_ILOAD_2 = 28
OPC_ILOAD_3 = 29
OPC_LLOAD_0 = 30
OPC_LLOAD_1 = 31
OPC_LLOAD_2 = 32
OPC_LLOAD_3 = 33
OPC_FLOAD_0 = 34
OPC_FLOAD_1 = 35
OPC_FLOAD_2 = 36
OPC_FLOAD_3 = 37
OPC_DLOAD_0 = 38
OPC_DLOAD_1 = 39
OPC_DLOAD_2 = 40
OPC_DLOAD_3 = 41
OPC_ALOAD_0 = 42
OPC_ALOAD_1 = 43
OPC_ALOAD_2 = 44
OPC_ALOAD_3 = 45
OPC_IALOAD = 46
OPC_LALOAD = 47
OPC_FALOAD = 48
OPC_DALOAD = 49
OPC_AALOAD = 50
OPC_BALOAD = 51
OPC_CALOAD = 52
OPC_SALOAD = 53
OPC_ISTORE = 54
OPC_LSTORE = 55
OPC_FSTORE = 56
OPC_DSTORE = 57
OPC_ASTORE = 58
OPC_ISTORE_0 = 59
OPC_ISTORE_1 = 60
OPC_ISTORE_2 = 61
OPC_ISTORE_3 = 62
OPC_LSTORE_0 = 63
OPC_LSTORE_1 = 64
OPC_LSTORE_2 = 65
OPC_LSTORE_3 = 66
OPC_FSTORE_0 = 67
OPC_FSTORE_1 = 68
OPC_FSTORE_2 = 69
OPC_FSTORE_3 = 70
OPC_DSTORE_0 = 71
OPC_DSTORE_1 = 72
OPC_DSTORE_2 = 73
OPC_DSTORE_3 = 74
OPC_ASTORE_0 = 75
OPC_ASTORE_1 = 76
OPC_ASTORE_2 = 77
OPC_ASTORE_3 = 78
OPC_IASTORE = 79
OPC_LASTORE = 80
OPC_FASTORE = 81
OPC_DASTORE = 82
OPC_AASTORE = 83
OPC_BASTORE = 84
OPC_CASTORE = 85
OPC_SASTORE = 86
OPC_POP = 87
OPC_POP2 = 88
OPC_DUP = 89
OPC_DUP_X1 = 90
OPC_DUP_X2 = 91
OPC_DUP2 = 92
OPC_DUP2_X1 = 93
OPC_DUP2_X2 = 94
OPC_SWAP = 95
OPC_IADD = 96
OPC_LADD = 97
OPC_FADD = 98
OPC_DADD = 99
OPC_ISUB = 100
OPC_LSUB = 101
OPC_FSUB = 102
OPC_DSUB = 103
OPC_IMUL = 104
OPC_LMUL = 105
OPC_FMUL = 106
OPC_DMUL = 107
OPC_IDIV = 108
OPC_LDIV = 109
OPC_FDIV = 110
OPC_DDIV = 111
OPC_IREM = 112
OPC_LREM = 113
OPC_FREM = 114
OPC_DREM = 115
OPC_INEG = 116
OPC_LNEG = 117
OPC_FNEG = 118
OPC_DNEG = 119
OPC_ISHL = 120
OPC_LSHL = 121
OPC_ISHR = 122
OPC_LSHR = 123
OPC_IUSHR = 124
OPC_LUSHR = 125
OPC_IAND = 126
OPC_LAND = 127
OPC_IOR = 128
OPC_LOR = 129
OPC_IXOR = 130
OPC_LXOR = 131
OPC_IINC = 132
OPC_I2L = 133
OPC_I2F = 134
OPC_I2D = 135
OPC_L2I = 136
OPC_L2F = 137
OPC_L2D = 138
OPC_F2I = 139
OPC_F2L = 140
OPC_F2D = 141
OPC_D2I = 142
OPC_D2L = 143
OPC_D2F = 144
OPC_I2B = 145
OPC_I2C = 146
OPC_I2S = 147
OPC_LCMP = 148
OPC_FCMPL = 149
OPC_FCMPG = 150
OPC_DCMPL = 151
OPC_DCMPG = 152
OPC_IFEQ = 153
OPC_IFNE = 154
OPC_IFLT = 155
OPC_IFGE = 156
OPC_IFGT = 157
OPC_IFLE = 158
OPC_IF_ICMPEQ = 159
OPC_IF_ICMPNE = 160
OPC_IF_ICMPLT = 161
OPC_IF_ICMPGE = 162
OPC_IF_ICMPGT = 163
OPC_IF_ICMPLE = 164
OPC_IF_ACMPEQ = 165
OPC_IF_ACMPNE = 166
OPC_GOTO = 167
OPC_JSR = 168
OPC_RET = 169
OPC_TABLESWITCH = 170
OPC_LOOKUPSWITCH = 171
OPC_IRETURN = 172
OPC_LRETURN = 173
OPC_FRETURN = 174
OPC_DRETURN = 175
OPC_ARETURN = 176
OPC_RETURN = 177
OPC_GETSTATIC = 178
OPC_PUTSTATIC = 179
OPC_GETFIELD = 180
OPC_PUTFIELD = 181
OPC_INVOKEVIRTUAL = 182
OPC_INVOKESPECIAL = 183
OPC_INVOKESTATIC = 184
OPC_INVOKEINTERFACE = 185
OPC_INVOKEDYNAMIC = 186
OPC_NEW = 187
OPC_NEWARRAY = 188
OPC_ANEWARRAY = 189
OPC_ARRAYLENGTH = 190
OPC_ATHROW = 191
OPC_CHECKCAST = 192
OPC_INSTANCEOF = 193
OPC_MONITORENTER = 194
OPC_MONITOREXIT = 195
OPC_WIDE = 196
OPC_MULTIANEWARRAY = 197
OPC_IFNULL = 198
OPC_IFNONNULL = 199
OPC_GOTO_W = 200
OPC_JSR_W = 201
OPC_BREAKPOINT = 202

# for backwards compatibility with 1.0
OPC_INT2BYTE = OPC_I2B
OPC_INT2CHAR = OPC_I2C
OPC_INT2SHORT = OPC_I2S
OPC_INVOKENONVIRTUAL = OPC_INVOKESPECIAL

# names of opcodes
OPC_NAMES = (
    "opc_nop", "opc_aconst_null", "opc_iconst_m1", "opc_iconst_0",
    "opc_iconst_1", "opc_iconst_2", "opc_iconst_3", "opc_iconst_4",
    "opc_iconst_5", "opc_lconst_0", "opc_lconst_1", "opc_fconst_0",
    "opc_fconst_1", "opc_fconst_2", "opc_dconst_0", "opc_dconst_1",
    "opc_bipush", "opc_sipush", "opc_ldc", "opc_ldc_w", "opc_ldc2_w",
    "opc_iload", "opc_lload", "opc_fload", "opc_dload", "opc_aload",
    "opc_iload_0", "opc_iload_1", "opc_iload_2", "opc_iload_3",
    "opc_lload_0", "opc_lload_1", "opc_lload_2", "opc_lload_3",
    "opc_fload_0", "opc_fload_1", "opc_fload_2", "opc_fload_3",
    "opc_dload_0", "opc_dload_1", "opc_dload_2", "opc_dload_3",
    "opc_aload_0", "opc_aload_1", "opc_aload_2", "opc_aload_3",
    "opc_iaload", "opc_laload", "opc_faload", "opc_daload", "opc_aaload",
    "opc_baload", "opc_caload", "opc_saload", "opc_istore", "opc_lstore",
    "opc_fstore", "opc_dstore", "opc_astore", "opc_istore_0",
    "opc_istore_1", "opc_istore_2", "opc_istore_3", "opc_lstore_0",
    "opc_lstore_1", "opc_lstore_2", "opc_lstore_3", "opc_fstore_0",
    "opc_fstore_1", "opc_fstore_2", "opc_fstore_3", "opc_dstore_0",
    "opc_dstore_1", "opc_dstore_2", "opc_dstore_3", "opc_astore_0",
    "opc_astore_1", "opc_astore_2", "opc_astore_3", "opc_iastore",
    "opc_lastore", "opc_fastore", "opc_dastore", "opc_aastore",
    "opc_bastore", "opc_castore", "opc_sastore", "opc_pop", "opc_pop2",
    "opc_dup", "opc_dup_x1", "opc_dup_x2", "opc_dup2", "opc_dup2_x1",
    "opc_dup2_x2", "opc_swap", "opc_iadd", "opc_ladd", "opc_fadd",
    "opc_dadd", "opc_isub", "opc_lsub", "opc_fsub", "opc_dsub", "opc_imul",
    "opc_lmul", "opc_fmul", "opc_dmul", "opc_idiv", "opc_ldiv", "opc_fdiv",
    "opc_ddiv", "opc_irem", "opc_lrem", "opc_frem", "opc_drem", "opc_ineg",
    "opc_lneg", "opc_fneg", "opc_dneg", "opc_ishl", "opc_lshl", "opc_ishr",
    "opc_lshr", "opc_iushr", "opc_lushr", "opc_iand", "opc_land", "opc_ior",
    "opc_lor", "opc_ixor", "opc_lxor", "opc_iinc", "opc_i2l", "opc_i2f",
    "opc_i2d", "opc_l2i", "opc_l2f", "opc_l2d", "opc_f2i", "opc_f2l",
    "opc_f2d", "opc_d2i", "opc_d2l", "opc_d2f", "opc_i2b", "opc_i2c",
    "opc_i2s", "opc_lcmp", "opc_fcmpl", "opc_fcmpg", "opc_dcmpl",
    "opc_dcmpg", "opc_ifeq", "opc_ifne", "opc_iflt", "opc_ifge", "opc_ifgt",
    "opc_ifle", "opc_if_icmpeq", "opc_if_icmpne", "opc_if_icmplt",
    "opc_if_icmpge", "opc_if_icmpgt", "opc_if_icmple", "opc_if_acmpeq",
    "opc_if_acmpne", "opc_goto", "opc_jsr", "opc_ret", "opc_tableswitch",
    "opc_lookupswitch", "opc_ireturn", "opc_lreturn", "opc_freturn",
    "opc_dreturn", "opc_areturn", "opc_return", "opc_getstatic",
    "opc_putstatic", "opc_getfield", "opc_putfield", "opc_invokevirtual",
    "opc_invokespecial", "opc_invokestatic", "opc_invokeinterface",
    "opc_invokedynamic", "opc_new", "opc_newarray", "opc_anewarray",
    "opc_arraylength", "opc_athrow", "opc_checkcast", "opc_instanceof",
    "opc_monitorenter", "opc_monitorexit", "opc_wide", "opc_multianewarray",
    "opc_ifnull", "opc_ifnonnull", "opc_goto_w", "opc_jsr_w",
    "opc_breakpoint",
)

# length of the opcodes (in bytes, including operands)
OPC_LENGTHS = (
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 3, 2, 3, 3, 2, 2, 2,
    2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 2, 99, 99, 1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3, 3, 5, 3, 3, 2, 3, 1,
    1, 3, 3, 1, 1, 0, 4, 3, 3, 5, 5, 1,
)
