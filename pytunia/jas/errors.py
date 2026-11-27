"""
The exception type of the jas library (port of jas.jasError).
"""


class JasError(Exception):
    """Raised for errors detected while building a class file."""

    def __init__(self, message=None):
        Exception.__init__(self, message)
        self.message = message

    def get_message(self):
        return "null" if self.message is None else self.message

    def __str__(self):
        # jasError.toString()
        if self.message is None:
            return "jas.jasError"
        return "jas.jasError: " + self.message
