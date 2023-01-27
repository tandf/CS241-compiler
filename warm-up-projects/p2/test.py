#! /bin/env python3

import unittest
from project2 import *
import io
import sys
import tempfile


class TestFileReader(unittest.TestCase):
    def test_filereader(self):
        code = "i - 5"
        with tempfile.NamedTemporaryFile() as tmp:
            file_name = tmp.name
            with open(tmp.name, "w") as f:
                f.write(code)
            reader = FileReader(tmp.name)
        self.assertEqual(reader.code, code)

        self.assertEqual(reader.getNext(), "i")
        self.assertEqual(reader.idx, 1)
        self.assertEqual((reader.line, reader.col), (1, 1))
        self.assertEqual(reader.file, file_name)

        self.assertEqual(reader.getNext(), " ")
        self.assertEqual(reader.idx, 2)
        self.assertEqual((reader.line, reader.col), (1, 2))

        self.assertEqual(reader.getNext(), "-")
        self.assertEqual(reader.idx, 3)
        self.assertEqual((reader.line, reader.col), (1, 3))

        self.assertEqual(reader.getNext(), " ")
        self.assertEqual(reader.idx, 4)
        self.assertEqual((reader.line, reader.col), (1, 4))

        self.assertEqual(reader.getNext(), "5")
        self.assertEqual(reader.idx, 5)
        self.assertEqual((reader.line, reader.col), (1, 5))

        self.assertEqual(reader.getNext(), FileReader.EOF)
        self.assertEqual(reader.idx, 5)
        self.assertEqual((reader.line, reader.col), (1, 5))

        self.assertEqual(reader.getNext(), FileReader.EOF)
        self.assertEqual(reader.idx, 5)
        self.assertEqual((reader.line, reader.col), (1, 5))

        sys.stderr = io.StringIO()
        error_msg = "test msg"
        reader.error(error_msg=error_msg)
        self.assertEqual(sys.stderr.getvalue(),
                         f"FileReader error <{reader.file}:1:5> {error_msg}\n")
        self.assertEqual(reader.getNext(), FileReader.ERROR)
        self.assertEqual(reader.idx, 5)


class TestTokennizer(unittest.TestCase):
    def test_tokenizer_id_table(self):
        # Test identifier table related functions
        t = Tokenizer("")
        n1 = "test_var"
        id1 = t.add_name(n1)
        self.assertEqual(id1, 0)
        self.assertEqual(t.id2string(id1), n1)
        self.assertEqual(t.string2id(n1), id1)

        n2 = "var2"
        id2 = t.add_name(n2)
        self.assertEqual(id2, 1)
        self.assertEqual(t.id2string(id2), n2)
        self.assertEqual(t.string2id(n2), id2)

        sys.stderr = io.StringIO()
        t.add_name(n2)
        self.assertEqual(sys.stderr.getvalue(),
                         f"Tokenizer error: Trying to add identifier {n2} for "
                         "the second time!\n")
        self.assertTrue(t.is_error)
        self.assertEqual(t.getNext().type, Token.ERROR)

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


class TestInterpreter(unittest.TestCase):
    def test_number(self):
        code = "1234 "
        with tempfile.NamedTemporaryFile() as tmp:
            with open(tmp.name, "w") as f:
                f.write(code)
            interpreter = Interpreter(tmp.name)
        self.assertEqual(interpreter.tokenizer.fileReader.code, code)
        self.assertEqual(interpreter.factor(), 1234)

        code = "(13) "
        with tempfile.NamedTemporaryFile() as tmp:
            with open(tmp.name, "w") as f:
                f.write(code)
            interpreter = Interpreter(tmp.name)
        self.assertEqual(interpreter.tokenizer.fileReader.code, code)
        self.assertEqual(interpreter.factor(), 13)

    def test_term(self):
        code = "33 * 3 / 11 "
        with tempfile.NamedTemporaryFile() as tmp:
            with open(tmp.name, "w") as f:
                f.write(code)
            interpreter = Interpreter(tmp.name)
        self.assertEqual(interpreter.tokenizer.fileReader.code, code)
        self.assertEqual(interpreter.term(), 9)

    def test_expression(self):
        code = "1 + 3 ;"
        with tempfile.NamedTemporaryFile() as tmp:
            with open(tmp.name, "w") as f:
                f.write(code)
            interpreter = Interpreter(tmp.name)
        self.assertEqual(interpreter.tokenizer.fileReader.code, code)
        self.assertEqual(interpreter.expression(), 4)

    def test_assignment(self):
        code = "var var1 <- 32 ;"
        with tempfile.NamedTemporaryFile() as tmp:
            with open(tmp.name, "w") as f:
                f.write(code)
            interpreter = Interpreter(tmp.name)
        self.assertEqual(interpreter.tokenizer.fileReader.code, code)

        interpreter.assignment()
        self.assertEqual(len(interpreter.identifiers), 1)
        id = interpreter.tokenizer.string2id("var1")
        self.assertEqual(interpreter.identifiers[id], 32)

    def compute(self, code: str):
        with tempfile.NamedTemporaryFile() as tmp:
            with open(tmp.name, "w") as f:
                f.write(code)
            interpreter = Interpreter(tmp.name)
        self.assertEqual(interpreter.tokenizer.fileReader.code, code)

        sys.stdout = io.StringIO()
        interpreter.computation()
        return sys.stdout.getvalue()

    def test_computation(self):
        code = """computation
        var var1 <- 32 ;
        var var2 <-15;
        var1 - var2;
        var1+var2.
        """
        self.assertEqual(self.compute(code), "17\n47\n")

        code = """computation
        var var1 <- 32 ;
        var var2 <- var1 - 15;
        var1 - var2;
        var1+var2.
        """
        self.assertEqual(self.compute(code), "15\n49\n")

        code = """computation
        var var1 <- 4 ;
        var var2 <- var1 - 2;
        var var1 <- 3;
        var asdf <- 1;
        var1 - var2;
        var1*var2;
        asdf + var1 + var2.
        """
        self.assertEqual(self.compute(code), "1\n6\n6\n")


if __name__ == "__main__":
    unittest.main()
