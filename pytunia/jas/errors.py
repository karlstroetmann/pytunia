"""
The exception type of the jas library (port of jas.jasError).
"""


class JasError(Exception):
    """Raised for errors detected while building a class file.

    ``num_tag`` is True when the error refers to the last integer that
    was read by the scanner; the error report then shows the position of
    that integer instead of the current scanner position.
    """

    def __init__(self, message=None, num_tag=False):
        Exception.__init__(self, message)
        self.message = message
        self.num_tag = num_tag

    def get_message(self):
        return "null" if self.message is None else self.message

    def __str__(self):
        # jasError.toString()
        if self.message is None:
            return "jas.jasError"
        return "jas.jasError: " + self.message
