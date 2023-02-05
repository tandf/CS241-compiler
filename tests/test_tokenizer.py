import sys
import os

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/..")

import unittest
from Tokenizer import Tokenizer, Token
import io
import tempfile


class TestTokennizer(unittest.TestCase):
    def test_tokenizer_id_table(self):
        # Test identifier table related functions
        code = ""
        with tempfile.NamedTemporaryFile() as tmp:
            with open(tmp.name, "w") as f:
                f.write(code)
            tokenizer = Tokenizer(tmp.name)
        self.assertEqual(tokenizer.fileReader.code, code)

        n1 = "test_var"
        id1 = tokenizer.add_name(n1)
        self.assertEqual(id1, 0)
        self.assertEqual(tokenizer.id2string(id1), n1)
        self.assertEqual(tokenizer.string2id(n1), id1)

        n2 = "var2"
        id2 = tokenizer.add_name(n2)
        self.assertEqual(id2, 1)
        self.assertEqual(tokenizer.id2string(id2), n2)
        self.assertEqual(tokenizer.string2id(n2), id2)

        sys.stderr = io.StringIO()
        tokenizer.add_name(n2)
        self.assertEqual(sys.stderr.getvalue(),
                         f"Tokenizer error: Trying to add identifier {n2} for "
                         "the second time!\n")
        self.assertTrue(tokenizer.is_error)
        self.assertEqual(tokenizer.getNext().type, Token.ERROR)
        sys.stderr = sys.__stderr__

    def test_tokenizer(self):
        code = "var1 - 15"
        with tempfile.NamedTemporaryFile() as tmp:
            with open(tmp.name, "w") as f:
                f.write(code)
            tokenizer = Tokenizer(tmp.name)
        self.assertEqual(tokenizer.fileReader.code, code)

        token = tokenizer.getNext()
        self.assertEqual(token.line, 1)
        self.assertEqual(token.col, 1)
        self.assertEqual(token.type, Token.IDENT)
        self.assertEqual(token.sym, "var1")
        self.assertEqual(tokenizer.id, tokenizer.string2id(token.sym))

        token = tokenizer.getNext()
        self.assertEqual(token.line, 1)
        self.assertEqual(token.col, 6)
        self.assertEqual(token.type, Token.MINUS)
        self.assertEqual(token.sym, "-")

        token = tokenizer.getNext()
        self.assertEqual(token.line, 1)
        self.assertEqual(token.col, 8)
        self.assertEqual(token.type, Token.NUMBER)
        self.assertEqual(token.sym, "15")
        self.assertEqual(tokenizer.num, 15)

    def test_tokenizer_multiline(self):
        code = """var1 <- 32 ;
 var2 <-15; var1 - var2;
.
"""

        with tempfile.NamedTemporaryFile() as tmp:
            with open(tmp.name, "w") as f:
                f.write(code)
            tokenizer = Tokenizer(tmp.name)
        self.assertEqual(tokenizer.fileReader.code, code)

        token = tokenizer.getNext()
        self.assertEqual((token.line, token.col), (1, 1))
        self.assertEqual(token.type, Token.IDENT)
        self.assertEqual(token.sym, "var1")
        self.assertEqual(tokenizer.id, tokenizer.string2id(token.sym))

        token = tokenizer.getNext()
        self.assertEqual((token.line, token.col), (1, 6))
        self.assertEqual(token.type, Token.BECOMES)
        self.assertEqual(token.sym, "<-")

        token = tokenizer.getNext()
        self.assertEqual((token.line, token.col), (1, 9))
        self.assertEqual(token.type, Token.NUMBER)
        self.assertEqual(token.sym, "32")
        self.assertEqual(tokenizer.num, 32)

        token = tokenizer.getNext()
        self.assertEqual((token.line, token.col), (1, 12))
        self.assertEqual(token.type, Token.SEMI)
        self.assertEqual(token.sym, ";")

        token = tokenizer.getNext()
        self.assertEqual((token.line, token.col), (2, 2))
        self.assertEqual(token.type, Token.IDENT)
        self.assertEqual(token.sym, "var2")
        self.assertEqual(tokenizer.id, tokenizer.string2id(token.sym))

        token = tokenizer.getNext()
        self.assertEqual((token.line, token.col), (2, 7))
        self.assertEqual(token.type, Token.BECOMES)
        self.assertEqual(token.sym, "<-")

        token = tokenizer.getNext()
        self.assertEqual((token.line, token.col), (2, 9))
        self.assertEqual(token.type, Token.NUMBER)
        self.assertEqual(token.sym, "15")
        self.assertEqual(tokenizer.num, 15)

        token = tokenizer.getNext()
        self.assertEqual((token.line, token.col), (2, 11))
        self.assertEqual(token.type, Token.SEMI)
        self.assertEqual(token.sym, ";")

        token = tokenizer.getNext()
        self.assertEqual((token.line, token.col), (2, 13))
        self.assertEqual(token.type, Token.IDENT)
        self.assertEqual(token.sym, "var1")
        self.assertEqual(tokenizer.id, tokenizer.string2id(token.sym))

        token = tokenizer.getNext()
        self.assertEqual((token.line, token.col), (2, 18))
        self.assertEqual(token.type, Token.MINUS)
        self.assertEqual(token.sym, "-")

        token = tokenizer.getNext()
        self.assertEqual((token.line, token.col), (2, 20))
        self.assertEqual(token.type, Token.IDENT)
        self.assertEqual(token.sym, "var2")
        self.assertEqual(tokenizer.id, tokenizer.string2id(token.sym))

        token = tokenizer.getNext()
        self.assertEqual((token.line, token.col), (2, 24))
        self.assertEqual(token.type, Token.SEMI)
        self.assertEqual(token.sym, ";")

        token = tokenizer.getNext()
        self.assertEqual((token.line, token.col), (3, 1))
        self.assertEqual(token.type, Token.PERIOD)
        self.assertEqual(token.sym, ".")
