import sys
import os

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/..")

import unittest
from SmplCompiler import SmplCompiler
import io
import tempfile


class TestParser(unittest.TestCase):
    def test_parser(self):
        pass