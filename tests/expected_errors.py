"""
The errors that pytunia reports for the test cases that contain errors.

pytunia does not reproduce Jasmin's error messages, so for these cases the
tests only check that no class file is generated, that the output has the
form of an error report, and that the first error refers to the line
given here (None: the error refers to no line).
"""

import re

ERROR_LINES = {
    'ErrAnnFloatNeg': 4, 'ErrAnnNotClosed': 5, 'ErrAnnParam': 4,
    'ErrAnnRange': 4, 'ErrAnnSig': 4, 'ErrAnnTooMany': 4, 'ErrAnnValue': 4,
    'ErrArrayType': 6, 'ErrAttrFile': 3, 'ErrBadArgs': 6, 'ErrBadArgs2': 6,
    'ErrBadArgs3': 6, 'ErrBadArgs4': 6, 'ErrBadEscape': 6, 'ErrBadNumber': 6,
    'ErrBadNumber2': 6, 'ErrBadNumber3': 6, 'ErrBadNumber4': 6,
    'ErrBadUEscape': 6, 'ErrBipush': 6, 'ErrBytecodeDouble': 1,
    'ErrBytecodeExp': 1, 'ErrBytecodeInt': 1, 'ErrBytecodeLong': 1,
    'ErrCatchMixed': 6, 'ErrDirectiveNumber': 3, 'ErrDollar': 6,
    'ErrDollarBad': 6, 'ErrDoubleClass': 3, 'ErrEmpty': None,
    'ErrEmptyName': 6, 'ErrEndField': 3, 'ErrFarJump': None,
    'ErrFieldNoClass': 6, 'ErrFieldValue': 3, 'ErrGloups': 6,
    'ErrInterfaceNargs': 6, 'ErrLabelSyntax': 7, 'ErrLimit': 4,
    'ErrLimitWord': 4, 'ErrMalformedSig': 6, 'ErrManyErrors': 4,
    'ErrMetho': 3, 'ErrMissingArgs': 6, 'ErrNameEscape': 6, 'ErrNameNoSep': 6,
    'ErrNewarrayInt': 6, 'ErrNoEndMethod': 4, 'ErrNoNewlineAtEnd': 4,
    'ErrNoSuper': 2, 'ErrOnlyComments': None, 'ErrRecovery': 7, 'ErrSet': 7,
    'ErrSignatureOutside': 4, 'ErrSipush': 6, 'ErrStackOffset2': 6,
    'ErrStackType': 7, 'ErrStackUse0': 4, 'ErrTableHigh': 7, 'ErrTabs': 4,
    'ErrUndefinedLabel': None, 'ErrUnknownDirective': 3, 'ErrUntermName': 6,
    'ErrUntermString': 6, 'ErrUntermStringEOF': 4, 'ErrVar': 6,
}


def check_error_report(test, name, report):
    """Checks the error report (standard error of the command line, or
    str(AssemblyError) followed by a line break) for the case ``name``."""
    filename = name + '.j'
    test.assertIn(name, ERROR_LINES, 'no expected error line for ' + name)
    line = ERROR_LINES[name]
    first = filename + (':' if line is None else ':%d:' % line) + ' '
    test.assertTrue(report.startswith(first),
                    'the report should start with %r:\n%s' % (first, report))
    m = re.search(r'^%s: Found (\d+) errors\n\Z' % re.escape(filename),
                  report, re.M)
    test.assertTrue(m and int(m.group(1)) >= 1,
                    'the report should end with "Found n errors":\n'
                    + report)
