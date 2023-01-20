#! /bin/env python3

import sys
from typing import Tuple


class FileReader:
    ERROR = 0
    EOF = 255

    def __init__(self, file: str):
        self.code = ""
        self.idx = 0
        self.is_error = False

        # For debugging
        self.line = 1
        self.col = 0
        self.file = file

        self.open()

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.col}"

    def debug_info(self) -> Tuple[str, int, int]:
        return self.file, self.line, self.col

    def open(self) -> None:
        try:
            with open(self.file) as f:
                self.code = f.read()
        except:
            self.error(f"Fail to open file {self.file}")

    def error(self, error_msg: str) -> None:
        self.is_error = True
        print(
            f"FileReader error <{self.__str__()}> {error_msg}", file=sys.stderr)

    def end(self) -> bool:
        return self.idx >= len(self.code)

    def getNext(self) -> str:
        if self.is_error:
            return self.ERROR
        elif self.end():
            return self.EOF
        else:
            if self.idx > 0 and self.code[self.idx - 1] == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            sym = self.code[self.idx]
            self.idx += 1
            return sym


class Token:
    ERROR = 0
    TIMES = 1  # *
    DIV = 2  # /
    PLUS = 11  # +
    MINUS = 12  # -
    EQL = 20  # ==
    NEQ = 21  # !=
    LSS = 22  # <
    GEQ = 23  # >=
    LEQ = 24  # <=
    GTR = 25  # >
    PERIOD = 30  # .
    COMMA = 31  # ,
    OPENBRACKET = 32  # [
    CLOSEBRACKET = 34  # ]
    CLOSEPAREN = 35  # )
    BECOMES = 40  # <-
    THEN = 41  # then
    DO = 42  # do
    OPENPAREN = 50  # (
    NUMBER = 60  # number
    IDENT = 61  # identifier
    SEMI = 70  # ;
    END = 80  # }
    OD = 81  # od
    FI = 82  # fi
    ELSE = 90  # else
    LET = 100  # let
    CALL = 101  # call
    IF = 102  # if
    WHILE = 103  # while
    RETURN = 104  # return
    VAR = 110  # var
    ARR = 111  # array
    VOID = 112  # void
    FUNC = 113  # function
    PROC = 114  # procedure
    BEGIN = 150  # {
    MAIN = 200  # computation
    EOF = 255  # end of file
    
    SYMBOLS = {
        "*": TIMES,
        "/": DIV,
        "+": PLUS,
        "-": MINUS,
        "==": EQL,
        "!=": NEQ,
        "<": LSS,
        ">=": GEQ,
        "<=": LEQ,
        ">": GTR,
        ".": PERIOD,
        ",": COMMA,
        "[": OPENBRACKET,
        "]": CLOSEBRACKET,
        ")": CLOSEPAREN,
        "<-": BECOMES,
        "(": OPENPAREN,
        ";": SEMI,
        "}": END,
        "{": BEGIN,
    }

    RESERVED_WORDS = {
        "then": THEN,
        "do": DO,
        "od": OD,
        "fi": FI,
        "else": ELSE,
        "let": LET,
        "call": CALL,
        "if": IF,
        "while": WHILE,
        "return": RETURN,
        "var": VAR,
        "array": ARR,
        "void": VOID,
        "function": FUNC,
        "procedure": PROC,
        "computation": MAIN,
    }

    def __init__(self, file: str, line: int, col: int):
        self.file = file
        self.line = line
        self.col = col

        self.sym = ""
        self.type = self.ERROR  # Unset

    def __str__(self) -> str:
        return f"{self.sym} (type: {self.type}) <{self.file}:{self.line}:{self.col}>"

class Tokenizer:
    def __init__(self, file: str):
        self.code = ""
        self.file = file
        self.fileReader = None

        # States
        self.is_error = False
        self.inputSym = None
        self.num = None
        self.id = None

        # ID - Name mapping
        self.id_cnt = 0
        self.ids = {}  # identifier: identifier id
        self.names = {}  # identifier id: identifier

        self.open()
        self.next()  # Read the first char
        self.clear_white_space()

    def error(self, error_msg: str) -> None:
        self.is_error = True
        print(f"Tokenizer error: {error_msg}", file=sys.stderr)

    def open(self) -> None:
        self.fileReader = FileReader(self.file)

    def next(self) -> None:
        if self.is_error:
            return
        self.inputSym = self.fileReader.getNext()
        if self.inputSym == self.fileReader.ERROR:
            self.error(f"Error in file reader {self.fileReader}")

    def id2string(self, id: int) -> str:
        assert id in self.names
        assert id == self.ids[self.names[id]]
        return self.names[id]

    def string2id(self, name: str) -> int:
        assert name in self.ids
        assert name == self.names[self.ids[name]]
        return self.ids[name]

    def add_name(self, name: str) -> int:
        if name in self.ids:
            self.error(f"Trying to add identifier {name} for the second time!")
            return None
        else:
            self.ids[name] = self.id_cnt
            self.names[self.id_cnt] = name
            self.id_cnt += 1
            return self.id_cnt - 1

    def is_white_space(self) -> bool:
        assert self.inputSym != None
        return self.inputSym in [" ", "\t", "\n"]

    def is_digit(self) -> bool:
        assert self.inputSym != None
        return ord(self.inputSym) >= ord("0") and ord(self.inputSym) <= ord("9")

    def is_letter(self) -> bool:
        assert self.inputSym != None
        if ord(self.inputSym) >= ord("a") and ord(self.inputSym) <= ord("z"):
            return True
        elif ord(self.inputSym) >= ord("A") and ord(self.inputSym) <= ord("Z"):
            return True
        else:
            return False

    def clear_white_space(self) -> None:
        if self.inputSym == FileReader.EOF:
            return
        while self.is_white_space():
            self.next()

    def create_token(self) -> Token:
        return Token(*self.fileReader.debug_info())

    def number(self) -> Token:
        token = self.create_token()
        result = 0
        sym = ""

        # Parse the number
        while self.inputSym != FileReader.EOF and self.is_digit():
            result = result * 10 + int(self.inputSym)
            sym += self.inputSym
            self.next()

        # Consume following white spaces. Prepare for parsing the next token.
        self.clear_white_space()

        self.num = result
        token.sym = sym
        token.type = Token.NUMBER
        return token

    def identifier(self) -> Token:
        token = self.create_token()

        # Consume the first letter
        sym = self.inputSym
        self.next()
        # Consume the following digits and letters
        while self.inputSym != FileReader.EOF and (self.is_digit() or self.is_letter()):
            sym += self.inputSym
            self.next()

        # Consume following white spaces. Prepare for parsing the next token.
        self.clear_white_space()

        token.sym  = sym
        if sym in Token.RESERVED_WORDS:
            token.type = Token.RESERVED_WORDS[sym]
        else:
            token.type = Token.IDENT
            # Add to the tables if neccessary. Set id
            if sym not in self.ids:
                self.add_name(sym)
            self.id = self.ids[sym]

        return token

    def operator(self) -> Token:
        token = self.create_token()
        sym = self.inputSym
        self.next()

        # Parse two-char operators
        if sym == "<":
            if self.inputSym in ["=", "-"]:
                sym += self.inputSym
                self.next()
        elif sym == ">":
            if self.inputSym == "=":
                sym += self.inputSym
                self.next()
        elif sym in ["=", "!"]:
            if self.inputSym != "=":
                token.sym = sym
                token.type = Token.ERROR
                self.error(f"Fail to parse token: {token}")
                return token
            sym += self.inputSym
            self.next()

        # Consume following white spaces. Prepare for parsing the next token.
        self.clear_white_space()

        token.sym = sym
        if sym in Token.SYMBOLS:
            token.type = Token.SYMBOLS[sym]
        else:
            token.type = Token.ERROR
            self.error(f"Unknown symbol: {token}")

        return token

    def getNext(self) -> Token:
        if self.is_error:
            token = self.create_token()
            token.type = Token.ERROR
            return token

        if self.is_digit():
            return self.number()
        elif self.is_letter():
            return self.identifier()
        else:
            return self.operator()

class Project2:
    def __init__(self, tokenizer: Tokenizer):
        self.tokenizer = tokenizer

    def sym(self) -> str:
        return self.tokenizer.sym()

    def is_white_space(self) -> bool:
        return self.tokenizer.is_white_space()

    def next(self) -> None:
        self.tokenizer.next()

    def clear_white_space(self) -> None:
        while self.is_white_space():
            self.tokenizer.next()

    def is_digit(self) -> bool:
        return self.tokenizer.is_digit()

    def number(self) -> int:
        result = 0
        while self.is_digit():
            result = result * 10 + int(self.sym())
            self.next()
        self.clear_white_space()
        return result

    def factor(self) -> int:
        if self.is_digit():
            return self.number()
        elif self.sym() == "(":
            self.next()
            self.clear_white_space()
            result = self.expression()
            assert self.sym() == ")", "unmatched parentheses in factor!"
            self.next()
            self.clear_white_space()
            return result
        else:
            assert False, f"factor starts with unexpected symbol \"{self.sym()}\""

    def term(self) -> int:
        result = self.factor()

        while True:
            if self.sym() == "*":
                self.next()
                self.clear_white_space()
                result *= self.factor()
            elif self.sym() == "/":
                self.next()
                self.clear_white_space()
                result /= self.factor()
            else:
                return result

    def expression(self) -> int:
        result = self.term()

        while True:
            if self.sym() == "+":
                self.next()
                self.clear_white_space()
                result += self.term()
            elif self.sym() == "-":
                self.next()
                self.clear_white_space()
                result -= self.term()
            else:
                return result

    def computation(self) -> int:
        self.clear_white_space()
        result = self.expression()
        while self.is_white_space():
            self.next()
        assert self.sym() == ".", "computation doesn't end with \".\"!"
        self.next()
        return result


if __name__ == "__main__":

    with open("input.txt", "r") as f:
        code = f.read()
        print(f"reading code: {code}")

    with open("answers.txt", "r") as f:
        answers = f.read().split()
    ans_idx = 0

    t = Tokenizer(code)
    p = Project2(t)
    print(f"results:")
    while not t.end():
        result = p.computation()
        print(f"\t{result} ", end="")
        if ans_idx < len(answers) and result == int(answers[ans_idx]):
            print("[correct]")
        else:
            print("[wrong]")
        ans_idx += 1
