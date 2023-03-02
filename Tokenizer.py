#! /bin/env python3

import sys
from typing import Tuple, Dict


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
                self.code = f.read().expandtabs(tabsize=4)
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
    
    # relOp = "==" | "!=" | "<" | "<=" | ">" | ">="
    RELOPS = [EQL, NEQ, LSS, GEQ, LEQ, GTR]

    TokenName = {
        ERROR: "ERROR",
        TIMES: "TIMES",
        DIV: "DIV",
        PLUS: "PLUS",
        MINUS: "MINUS",
        EQL: "EQL",
        NEQ: "NEQ",
        LSS: "LSS",
        GEQ: "GEQ",
        LEQ: "LEQ",
        GTR: "GTR",
        PERIOD: "PERIOD",
        COMMA: "COMMA",
        OPENBRACKET: "OPENBRACKET",
        CLOSEBRACKET: "CLOSEBRACKET",
        CLOSEPAREN: "CLOSEPAREN",
        BECOMES: "BECOMES",
        THEN: "THEN",
        DO: "DO",
        OPENPAREN: "OPENPAREN",
        NUMBER: "NUMBER",
        IDENT: "IDENT",
        SEMI: "SEMI",
        END: "END",
        OD: "OD",
        FI: "FI",
        ELSE: "ELSE",
        LET: "LET",
        CALL: "CALL",
        IF: "IF",
        WHILE: "WHILE",
        RETURN: "RETURN",
        VAR: "VAR",
        ARR: "ARR",
        VOID: "VOID",
        FUNC: "FUNC",
        PROC: "PROC",
        BEGIN: "BEGIN",
        MAIN: "MAIN",
        EOF: "EOF",
    }

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
        "main": MAIN,
    }

    file: str
    line: int
    col: int
    sym: str
    type: int

    def __init__(self, file: str, line: int, col: int):
        self.file = file
        self.line = line
        self.col = col

        self.sym = ""
        self.type = self.ERROR  # Unset

    def __str__(self) -> str:
        return f'"{self.sym}" ({self.TokenName[self.type]}) ' + \
            f'{self.file}:{self.line}:{self.col}'

    def __repr__(self) -> str:
        return self.__str__()

    def source_loc(self) -> str:
        with open(self.file, "r") as f:
            lines = f.readlines()
        assert len(lines) > self.line-1

        code_line = lines[self.line-1].expandtabs(tabsize=4)
        if len(code_line) <= self.col + len(self.sym) - 2:
            print(code_line)
            print(len(code_line), self.col, len(self.sym))
        assert len(code_line) > self.col + len(self.sym) - 2

        file_loc = f"{self.file}({self.line}:{self.col})\n"

        return f"{file_loc}{code_line}{' '*(self.col-1)}{'^'*len(self.sym)}"

class Tokenizer:
    ids: Dict[str, int]
    names: Dict[int, str]

    def __init__(self, file: str):
        self.file = file
        self.fileReader = FileReader(self.file)

        # States
        self.is_error = False
        self.inputSym = None
        self.num = None
        self.id = None

        # ID - Name mapping
        self.id_cnt = 0
        self.ids = {}  # identifier: identifier id
        self.names = {}  # identifier id: identifier

        self.next()  # Read the first char
        self.clear_white_space()

    def error(self, error_msg: str) -> None:
        self.is_error = True
        print(f"Tokenizer error: {error_msg}", file=sys.stderr)

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

        token.sym = sym
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
        if self.is_error or self.inputSym == FileReader.ERROR:
            token = self.create_token()
            token.type = Token.ERROR
            return token
        elif self.inputSym == FileReader.EOF:
            token = self.create_token()
            token.type = Token.EOF
            return token
        elif self.is_digit():
            return self.number()
        elif self.is_letter():
            return self.identifier()
        else:
            return self.operator()
