#! /bin/env python3

from Tokenizer import Tokenizer, Token
from typing import Callable, List
from functools import wraps


class SmplCompiler:
    def __init__(self, file: str, debug=False):
        self.file = file
        self.tokenizer = Tokenizer(self.file)
        self.inputSym = None
        self.debug = debug

        # Read the first token
        self.next()

    def next(self) -> None:
        if self.debug and self.inputSym:
            print(f"  {self.inputSym}")
        self.inputSym = self.tokenizer.getNext()

    def _check_token(self, token: int, msg: str):
        self._check_tokens([token], msg=msg)

    def _check_tokens(self, tokens: List[int], msg: str):
        assert self.inputSym.type in tokens, msg

    def _nonterminal(func: Callable):
        @wraps(func)
        def wrapNT(self):
            if self.debug:
                print(func.__name__)
            return func(self)
        return wrapNT

    @_nonterminal
    def designator(self):
        # designator = ident{ "[" expression "]" }

        self._check_token(Token.IDENT, 'Expecting identifier at the beginning '
                          f'of designator, found {self.inputSym}')
        self.next()

        while self.inputSym.type == Token.OPENBRACKET:
            self.next()

            self.expression()

            self._check_token(Token.CLOSEBRACKET,
                              f'Expecting "]", found {self.inputSym}')
            self.next()

    @_nonterminal
    def factor(self):
        # factor = designator | number | "(" expression ")" | funcCall

        if self.inputSym.type == Token.IDENT:
            id = self.tokenizer.id
            # assert id in self.identifiers, f"Uninitalized variable {self.inputSym.sym}"
            self.next()
            return

        elif self.inputSym.type == Token.NUMBER:
            num = self.tokenizer.num
            self.next()
            return

        elif self.inputSym.type == Token.OPENPAREN:
            self.next()
            self.expression()
            self._check_token(Token.CLOSEPAREN,
                              "Unmatched parentheses in factor!")
            self.next()
            return

        elif self.inputSym.type == Token.CALL:
            self.funcCall()

        else:
            raise Exception(
                f"Factor starts with unexpected token {self.inputSym}")

    @_nonterminal
    def term(self):
        # term = factor { ("*" | "/") factor}

        self.factor()

        while True:
            if self.inputSym.type == Token.TIMES:
                self.next()
                self.factor()
            elif self.inputSym.type == Token.DIV:
                self.next()
                self.factor()
            else:
                return

    @_nonterminal
    def expression(self):
        # expression = term {("+" | "-") term}

        self.term()

        while True:
            if self.inputSym.type == Token.PLUS:
                self.next()
                self.term()
            elif self.inputSym.type == Token.MINUS:
                self.next()
                self.term()
            else:
                return

    @_nonterminal
    def relation(self):
        # relation = expression relOp expression
        # TODO
        raise Exception("Unimplemented")

    @_nonterminal
    def assignment(self) -> None:
        # assignment = "let" designator "<-" expression

        self._check_token(
            Token.LET, f'Expecting keyword "let", found {self.inputSym}')
        self.next()

        self.designator()

        self._check_token(Token.BECOMES, 'Expecting "<-" after variable name, '
                          f'found {self.inputSym}')
        self.next()

        self.expression()

    @_nonterminal
    def funcCall(self):
        # funcCall = "call" ident [ "(" [expression { "," expression } ] ")" ]

        self._check_token(Token.CALL, 'Expecting keyword "call" at the '
                          f'begining of funcCall, found {self.inputSym}')
        self.next()

        self._check_token(Token.IDENT, 'Expecting function name, found '
                          f'{self.inputSym}')
        self.next()

        if self.inputSym.type == Token.OPENPAREN:
            self.next()

            while self.inputSym.type != Token.CLOSEPAREN:
                self.expression()

                if self.inputSym.type == Token.COMMA:
                    self.next()
                    assert self.inputSym.type != Token.CLOSEPAREN

            self._check_token(Token.CLOSEPAREN, 'Expecting ")", found '
                              f'{self.inputSym}')
            self.next()

        else:
            # TODO: functions without parameters can be called with or without
            # paranthese. Make sure function doesn't have parameters
            pass

    @_nonterminal
    def ifStatement(self):
        # ifStatement = "if" relation "then" statSequence [ "else" statSequence ] "fi"
        # TODO
        raise Exception("Unimplemented")

    @_nonterminal
    def whileStatement(self):
        # whileStatement = "while" relation "do" StatSequence "od"
        # TODO
        raise Exception("Unimplemented")

    @_nonterminal
    def returnStatement(self):
        # returnStatement = "return" [ expression ]
        # TODO
        raise Exception("Unimplemented")

    @_nonterminal
    def statement(self):
        # statement = assignment | funcCall | ifStatement | whileStatement | returnStatement

        if self.inputSym.type == Token.LET:
            self.assignment()
        elif self.inputSym.type == Token.CALL:
            self.funcCall()
        elif self.inputSym.type == Token.IF:
            self.ifStatement()
        elif self.inputSym.type == Token.WHILE:
            self.whileStatement
        elif self.inputSym.type == Token.RETURN:
            self.returnStatement

    @_nonterminal
    def statSequence(self):
        # statSequence = statement { ";" statement } [ ";" ]

        statement_tokens = [Token.LET, Token.CALL,
                             Token.IF, Token.WHILE, Token.RETURN]

        # Check for the first assignment
        self._check_tokens(statement_tokens,
                           f'Expecting statement, found {self.inputSym}')

        while self.inputSym.type in statement_tokens:
            self.statement()

            if self.inputSym.type == Token.SEMI:
                self.next()
            else:
                break

    @_nonterminal
    def typeDecl(self):
        # typeDecl = "var" | "array" "[" number "]" { "[" number "]" }

        if self.inputSym.type == Token.VAR:
            self.next()

        elif self.inputSym.type == Token.ARR:
            self.next()

            # Check for the first open bracket
            self._check_token(Token.OPENBRACKET,
                              f'Expecting "[", found {self.inputSym}')

            while self.inputSym.type == Token.OPENBRACKET:
                self.next()

                self._check_token(Token.NUMBER,
                                  f'Expecting number, found {self.inputSym}')
                self.next()

                self._check_token(Token.CLOSEBRACKET,
                                  f'Expecting "]", found {self.inputSym}')
                self.next()

        else:
            raise Exception('Excepting "var" or "array" at the beginning of '
                            f'typeDecl, found {self.inputSym}')

    @_nonterminal
    def varDecl(self):
        # varDecl = typeDecl ident { "," ident } ";"

        self.typeDecl()

        while True:
            self._check_token(Token.IDENT, 'Expecting identifier, found '
                              f'{self.inputSym}')
            self.next()

            if self.inputSym.type == Token.COMMA:
                self.next()
            elif self.inputSym.type == Token.SEMI:
                self.next()
                break
            else:
                raise Exception(f'Excepting "," or ";", found {self.inputSym}')

    @_nonterminal
    def funcDecl(self):
        # funcDecl = [ "void" ] "function" ident formalParam ";" funcBody ";"
        # TODO
        raise Exception("Unimplemented")

    @_nonterminal
    def formalParam(self):
        # formalParam = "(" [ident { "," ident }] ")"
        # TODO
        raise Exception("Unimplemented")

    @_nonterminal
    def funcBody(self):
        # funcBody = { varDecl } "{" [ statSequence ] "}"
        # TODO
        raise Exception("Unimplemented")

    @_nonterminal
    def computation(self):
        # computation = "main" { varDecl } { funcDecl } "{" statSequence "}" "."

        self._check_token(Token.MAIN, 'Expecting "main" at the start of '
                          f'computation, found {self.inputSym}')
        self.next()

        while self.inputSym.type == Token.VAR or self.inputSym.type == Token.ARR:
            self.varDecl()

        while self.inputSym.type == Token.VOID or self.inputSym.type == Token.FUNC:
            self.funcDecl()

        self._check_token(
            Token.BEGIN, f'Expecting "{{", found {self.inputSym}')
        self.next()

        self.statSequence()

        self._check_token(
            Token.END, f'Expecting "}}", found {self.inputSym}')
        self.next()

        self._check_token(Token.PERIOD, f'Expecting "." at the end of '
                          f'computation, found {self.inputSym}')
        self.next()

        return


if __name__ == "__main__":
    smplCompiler = SmplCompiler("code_example/code1.smpl", debug=True)
    smplCompiler.computation()
