#! /bin/env python3

from Tokenizer import Tokenizer, Token
from typing import Callable, List
from functools import wraps
from Block import *

class SmplCDebug:
    class NT:
        def __init__(self, name:str):
            self.name = name
            self.components = []

    def __init__(self, file:str=None):
        self.root = []
        self.current = self.root
        self.stack = []
        self.file = file

    def add(self, item):
        self.current.append(item)

    def push(self, func_name:str):
        nt = self.NT(func_name)
        self.add(nt)
        self.stack.append(self.current)
        self.current = nt.components

    def pop(self):
        self.current = self.stack.pop()

    def toStr(self, node:List, indent:int=0) -> str:
        string = ""

        for item in node:
            if isinstance(item, self.NT):
                string += f"{'| ' * indent}NT:{item.name}\n"
                string += self.toStr(indent=indent+1, node=item.components)
            elif isinstance(item, Token):
                string += f"{'| ' * indent}{item}\n"
            else:
                raise Exception("Internal error: debug node of unexpected "
                                f"type {type(node)}")

        return string

    def dump(self):
        if self.file:
            with open(self.file, "w+") as f:
                f.write(self.toStr(self.root))
        else:
            print(self.toStr(self.root))


class SmplCompiler:
    def __init__(self, file: str, debug: SmplCDebug = None):
        self.file = file
        self.debug = debug
        self.tokenizer = Tokenizer(self.file)
        self.inputSym = None

        # Read the first token
        self.next()

    def next(self) -> None:
        if self.debug and self.inputSym:
            self.debug.add(self.inputSym)
        self.inputSym = self.tokenizer.getNext()

    def _check_token(self, token: int, msg: str):
        self._check_tokens([token], msg=msg)

    def _check_tokens(self, tokens: List[int], msg: str):
        assert self.inputSym.type in tokens, msg

    def _debug_print(self):
        print(self.inputSym.source_loc())

    def _nonterminal(func: Callable):
        @wraps(func)

        def wrapNT(self):
            try:
                if self.debug:
                    self.debug.push(func.__name__)
                ret = func(self)

            except Exception as e:
                if self.debug:
                    self.debug.dump()
                self._debug_print()
                raise e

            finally:
                if self.debug:
                    self.debug.pop()
            return ret

        return wrapNT

    @_nonterminal
    def designator(self) -> SimpleBB:
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
    def factor(self) -> SimpleBB:
        # factor = designator | number | "(" expression ")" | funcCall

        if self.inputSym.type == Token.IDENT:
            self.designator()

        elif self.inputSym.type == Token.NUMBER:
            num = self.tokenizer.num
            self.next()

        elif self.inputSym.type == Token.OPENPAREN:
            self.next()
            self.expression()
            self._check_token(Token.CLOSEPAREN,
                              "Unmatched parentheses in factor!")
            self.next()

        elif self.inputSym.type == Token.CALL:
            self.funcCall()

        else:
            raise Exception(
                f"Factor starts with unexpected token {self.inputSym}")

    @_nonterminal
    def term(self) -> SimpleBB:
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
    def expression(self) -> SimpleBB:
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
    def relation(self) -> SimpleBB:
        # relation = expression relOp expression

        self.expression()

        self._check_tokens(Token.RELOPS, 'Expecting relation operator, found '
                           f'{self.inputSym}')
        self.next()

        self.expression()

    @_nonterminal
    def assignment(self) -> SimpleBB:
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
    def funcCall(self) -> SimpleBB:
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
    def ifStatement(self) -> SuperBlock:
        # ifStatement = "if" relation "then" statSequence [ "else" statSequence ] "fi"

        self._check_token(Token.IF, 'Expecting "if" at the begining of '
                          f'ifStatement, found {self.inputSym}')
        self.next()
        self.relation()

        self._check_token(Token.THEN, 'Expecting "then" in ifStatement, found '
                          f'{self.inputSym}')
        self.next()
        self.statSequence()

        if self.inputSym.type == Token.ELSE:
            self.next()
            self.statSequence()

        self._check_token(Token.FI, 'Expecting "fi" at the end of ifStatement, '
                          f'found {self.inputSym}')
        self.next()

    @_nonterminal
    def whileStatement(self) -> SuperBlock:
        # whileStatement = "while" relation "do" StatSequence "od"

        self._check_token(Token.WHILE, 'Expecting "while" at the begining of '
                          f'whileStatement, found {self.inputSym}')
        self.next()
        self.relation()

        self._check_token(Token.DO, 'Expecting "do" in whileStatement, found '
                          f'{self.inputSym}')
        self.next()
        self.statSequence()

        self._check_token(Token.OD, 'Expecting "od" at the end of whileStatement, '
                          f'found {self.inputSym}')
        self.next()

    @_nonterminal
    def returnStatement(self) -> SimpleBB:
        # returnStatement = "return" [ expression ]

        self._check_token(Token.RETURN, 'Expecting "return" at the begining of '
                          f'returnStatement, found {self.inputSym}')
        self.next()

        if self.inputSym.type in [Token.IDENT, Token.NUMBER, Token.OPENPAREN, Token.CALL]:
            self.expression()

    @_nonterminal
    def statement(self) -> Block:
        # statement = assignment | funcCall | ifStatement | whileStatement | returnStatement

        if self.inputSym.type == Token.LET:
            self.assignment()
        elif self.inputSym.type == Token.CALL:
            self.funcCall()
        elif self.inputSym.type == Token.IF:
            self.ifStatement()
        elif self.inputSym.type == Token.WHILE:
            self.whileStatement()
        elif self.inputSym.type == Token.RETURN:
            self.returnStatement()
        else:
            raise Exception(f'Expecting statment, found {self.inputSym}')

    @_nonterminal
    def statSequence(self) -> SuperBlock:
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

        if self.inputSym.type == Token.VOID:
            self.next()

        self._check_token(Token.FUNC, 'Expecting keyword "function" at the '
                          f'beginning of funcDecl, found {self.inputSym}')
        self.next()

        self._check_token(Token.IDENT, 'Expecting identifier after keyword '
                          f'"function", found {self.inputSym}')
        self.next()

        self.formalParam()

        self._check_token(Token.SEMI, 'Expecting ";" after formalParam, '
                          f'found {self.inputSym}')
        self.next()

        self.funcBody()

        self._check_token(Token.SEMI, 'Expecting ";" after funcBody, '
                          f'found {self.inputSym}')
        self.next()

    @_nonterminal
    def formalParam(self):
        # formalParam = "(" [ident { "," ident }] ")"

        self._check_token(Token.OPENPAREN, 'Expecting "(" at the begining of '
                          f'formalParam, found {self.inputSym}')
        self.next()
        
        while self.inputSym.type == Token.IDENT:
            self.next()

            if self.inputSym.type == Token.COMMA:
                self.next()
                self._check_token(Token.IDENT, 'Expecting identifier after '
                                  f'comma, found {self.inputSym}')
            else:
                break

        self._check_token(Token.CLOSEPAREN, 'Expecting ")" at the end of '
                          f'formalParam, found {self.inputSym}')
        self.next()

    @_nonterminal
    def funcBody(self):
        # funcBody = { varDecl } "{" [ statSequence ] "}"

        while self.inputSym.type in [Token.VAR, Token.ARR]:
            self.varDecl()

        self._check_token(Token.BEGIN, 'Expecting "{" at the begining of '
                          f'funcBody, found {self.inputSym}')
        self.next()
        
        if self.inputSym.type != Token.END:
            self.statSequence()

        self._check_token(Token.END, 'Expecting "}" at the end of '
                          f'funcBody, found {self.inputSym}')
        self.next()


    @_nonterminal
    def computation(self):
        # computation = "main" { varDecl } { funcDecl } "{" statSequence "}" "."

        self._check_token(Token.MAIN, 'Expecting keyword "main" at the start '
                          f'of computation, found {self.inputSym}')
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
    smplCompiler = SmplCompiler("code_example/code1.smpl", debug=SmplCDebug(file="out.txt"))
    smplCompiler.computation()
    smplCompiler.debug.dump()
