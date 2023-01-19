#! /bin/env python3

import unittest
from project1 import Project1, Tokenizer

class TestProject1(unittest.TestCase):
    def test_number(self):
        t = Tokenizer("1234.")
        p = Project1(t)
        self.assertEqual(p.number(), 1234)

    def test_factor(self):
        t = Tokenizer("1234.")
        p = Project1(t)
        self.assertEqual(p.factor(), 1234)

        t = Tokenizer("1234 .")
        p = Project1(t)
        self.assertEqual(p.factor(), 1234)

        t = Tokenizer("(1234).")
        p = Project1(t)
        self.assertEqual(p.factor(), 1234)

    def test_term(self):
        t = Tokenizer("12 * 3.")
        p = Project1(t)
        self.assertEqual(p.term(), 36)

        t = Tokenizer("12 / 3 .")
        p = Project1(t)
        self.assertEqual(p.term(), 4)

    def test_expression(self):
        t = Tokenizer("12 - 3.")
        p = Project1(t)
        self.assertEqual(p.expression(), 9)

        t = Tokenizer("12 + 3.")
        p = Project1(t)
        self.assertEqual(p.expression(), 15)

    def test_computation(self):
        t = Tokenizer("1234.")
        p = Project1(t)
        self.assertEqual(p.computation(), 1234)

        t = Tokenizer(" 1234.")
        p = Project1(t)
        self.assertEqual(p.computation(), 1234)

        t = Tokenizer(" 3 * (2 + 3) * 4. 3 - 4 * 5 / ( 3 + 1).")
        p = Project1(t)
        while not t.end():
            self.assertEqual(p.computation(), 60)
            self.assertEqual(p.computation(), -2)

if __name__ == "__main__":
    unittest.main()