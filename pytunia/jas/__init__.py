"""
jas - a library for building Java class files.

This is a Python port of the JAS package that is used by the Jasmin
assembler.  The class and method names follow the Java original, with
method names converted to snake_case.
"""

from .errors import JasError
from .cp import (CP, AsciiCP, ClassCP, StringCP, IntegerCP, FloatCP, LongCP,
                 DoubleCP, NameTypeCP, FieldCP, MethodCP, InterfaceCP)
from .insn import (Insn, Label, LabelOrOffset, IincInsn, InvokeinterfaceInsn,
                   MultiarrayInsn, TableswitchInsn, LookupswitchInsn)
from .code import (CodeAttr, Catchtable, CatchEntry, LineTableAttr,
                   LocalVarEntry, LocalVarTableAttr, LocalVarTypeTableAttr)
from .attributes import (ExceptAttr, ConstAttr, SourceAttr, SignatureAttr,
                         DeprecatedAttr, SourceDebugExtensionAttr,
                         EnclosingMethodAttr, GenericAttr, InnerClass,
                         InnerClassesAttr)
from .annotation import (Annotation, AnnotationElement, AnnotationAttr,
                         AnnotParamAttr, AnnotDefAttr)
from .stackmap import StackMap, VerifyFrame, VerificationTypeInfo
from .classenv import ClassEnv, Method, Var
from . import constants
from . import stackmap

__all__ = [
    'JasError',
    'CP',
    'AsciiCP',
    'ClassCP',
    'StringCP',
    'IntegerCP',
    'FloatCP',
    'LongCP',
    'DoubleCP',
    'NameTypeCP',
    'FieldCP',
    'MethodCP',
    'InterfaceCP',
    'Insn',
    'Label',
    'LabelOrOffset',
    'IincInsn',
    'InvokeinterfaceInsn',
    'MultiarrayInsn',
    'TableswitchInsn',
    'LookupswitchInsn',
    'CodeAttr',
    'Catchtable',
    'CatchEntry',
    'LineTableAttr',
    'LocalVarEntry',
    'LocalVarTableAttr',
    'LocalVarTypeTableAttr',
    'ExceptAttr',
    'ConstAttr',
    'SourceAttr',
    'SignatureAttr',
    'DeprecatedAttr',
    'SourceDebugExtensionAttr',
    'EnclosingMethodAttr',
    'GenericAttr',
    'InnerClass',
    'InnerClassesAttr',
    'Annotation',
    'AnnotationElement',
    'AnnotationAttr',
    'AnnotParamAttr',
    'AnnotDefAttr',
    'StackMap',
    'VerifyFrame',
    'VerificationTypeInfo',
    'ClassEnv',
    'Method',
    'Var',
    'constants',
    'stackmap',
]
