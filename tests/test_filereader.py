import sys
import os

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/..")

import unittest
from Tokenizer import FileReader
import io
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

        sys.stderr = sys.__stderr__
