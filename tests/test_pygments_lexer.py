#!/usr/bin/env python3
"""
Tests of the lexer for Pygments in pytunia/pygments_lexer.py.  Sources in
the notation of Jasmin must be coloured as by the lexer of Jasmin that comes
with Pygments, and the types in Java notation must be coloured as types,
with the brackets "[]" and the commas between parameters as punctuation.
"""

import glob
import os
import sys
import tomllib
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

try:
    import pygments
except ImportError:
    pygments = None

from test_java_types import DESCRIPTORS, JAVA  # noqa


@unittest.skipUnless(pygments, 'Pygments is not installed')
class TestPygmentsLexer(unittest.TestCase):

    def tokens(self, lexer, text):
        """The tokens of text except blanks; fails if there is an error."""
        from pygments.token import Error
        tokens = [(t, v) for t, v in lexer.get_tokens(text) if v.strip()]
        self.assertEqual([v for t, v in tokens if t in Error], [])
        return tokens

    def test_jasmin_notation(self):
        from pygments.lexers.jvm import JasminLexer
        from pytunia.pygments_lexer import PytuniaLexer
        sources = [DESCRIPTORS]
        for path in sorted(glob.glob(os.path.join(HERE, 'cases', '*.j'))):
            with open(path, encoding='utf-8', errors='replace') as handle:
                sources.append(handle.read())
        for source in sources:
            self.assertEqual(list(PytuniaLexer().get_tokens(source)),
                             list(JasminLexer().get_tokens(source)))

    def test_java_notation(self):
        from pygments.token import Keyword, Name, Punctuation
        from pytunia.pygments_lexer import PytuniaLexer
        tokens = self.tokens(PytuniaLexer(), JAVA)
        for t, v in tokens:
            if t in Keyword.Type:
                self.assertNotRegex(v, r'[\[\],]')
        for expected in [(Keyword.Type, 'java.lang.String'),
                         (Keyword.Type, 'java.util.Map$Entry'),
                         (Keyword.Type, 'int'), (Keyword.Type, 'void'),
                         (Punctuation, '[]'), (Punctuation, '[][]'),
                         (Punctuation, ','),
                         (Name.Function, 'println'),
                         (Name.Namespace, 'java.lang.'),
                         (Name.Class, 'Object')]:
            self.assertIn(expected, tokens)

    def test_signature(self):
        from pygments.token import Keyword, Name, Punctuation
        from pytunia.pygments_lexer import PytuniaLexer
        source = 'invokestatic Main.max(java.lang.Long[], int) int\n'
        self.assertEqual(self.tokens(PytuniaLexer(), source), [
            (Keyword.Reserved, 'invokestatic'), (Name.Class, 'Main.'),
            (Name.Function, 'max'), (Punctuation, '('),
            (Keyword.Type, 'java.lang.Long'), (Punctuation, '[]'),
            (Punctuation, ','), (Keyword.Type, 'int'), (Punctuation, ')'),
            (Keyword.Type, 'int')])

    def test_entry_points(self):
        from pytunia import pygments_lexer
        with open(os.path.join(os.path.dirname(HERE), 'pyproject.toml'),
                  'rb') as handle:
            project = tomllib.load(handle)['project']
        entry_points = project['entry-points']['pygments.lexers']
        self.assertEqual(entry_points,
                         {'pytunia': 'pytunia.pygments_lexer:PytuniaLexer'})
        self.assertIn('pytunia', pygments_lexer.PytuniaLexer.aliases)


if __name__ == '__main__':
    unittest.main()
