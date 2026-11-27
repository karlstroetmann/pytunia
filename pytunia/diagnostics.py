"""
Error messages of the assembler.
"""


class Diagnostic(object):
    """One error message of the assembler.

    Attributes:

    ``filename``
        the name of the source file
    ``line``
        the line number (``None`` if the error does not refer to a line)
    ``message``
        the message, e.g. ``"JAS Error: bipush value exceed size of byte"``
    ``source_line``
        the source line that the error refers to (``None`` if not
        available)
    ``column``
        the position in ``source_line`` where the error was detected,
        counted from 0 (``None`` if the error refers to the whole line,
        e.g. to a statement)

    ``str(diagnostic)`` is the complete message: the file name, the line
    number and the message, then the source line and a caret below the
    column.
    """

    __slots__ = ('filename', 'line', 'message', 'source_line', 'column',
                 '_text')

    def __init__(self, filename, line, message, source_line, column, text):
        self.filename = filename
        self.line = line
        self.message = message
        self.source_line = source_line
        self.column = column
        self._text = text

    def __str__(self):
        return self._text

    def __repr__(self):
        return 'Diagnostic(%r, %r, %r)' % (self.filename, self.line,
                                           self.message)


class AssemblyError(Exception):
    """Raised when a Jasmin source contains errors.

    ``errors`` is the list of Diagnostic objects.  ``str(error)`` is the
    error output of the command line, including the final "Found N errors"
    line.
    """

    def __init__(self, filename, errors):
        Exception.__init__(self, filename, list(errors))
        self.filename = filename
        self.errors = list(errors)

    def __str__(self):
        lines = [str(d) for d in self.errors]
        lines.append("%s: Found %d errors" % (self.filename,
                                              len(self.errors)))
        return '\n'.join(lines)
