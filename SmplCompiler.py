#! /bin/env python3

from Tokenizer import Tokenizer, Token
from typing import Callable, List, Tuple
from functools import wraps
from Block import *
from IRVis import IRVis


class SmplCDebug:
    class NT:
        def __init__(self, name: str):
            self.name = name
            self.components = []

    def __init__(self, file: str = None):
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

    def toStr(self, node: List, indent: int = 0) -> str:
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
    file: str
    debug: SmplCDebug
    tokenizer: Tokenizer
    inputSym: Token
    computationBlock: SuperBlock

    def __init__(self, file: str, debug: SmplCDebug = None):
        self.file = file
        self.debug = debug
        self.tokenizer = Tokenizer(self.file)
        self.inputSym = None
        self.computationBlock = SuperBlock("computation block")
        # TODO: define variable table, used to track types of variables

        self._debug_printed = False

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
        if not self._debug_printed:
            print(self.inputSym.source_loc())
            self._debug_printed = True

    def _nonterminal(func: Callable):
        @wraps(func)
        def wrapNT(self, *args, **kargs):
            try:
                if self.debug:
                    self.debug.push(func.__name__)
                ret = func(self, *args, **kargs)

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
    def designator(self, context: SimpleBB):
        # TODO: simple example
        # designator = ident{ "[" expression "]" }

        self._check_token(Token.IDENT, 'Expecting identifier at the beginning '
                          f'of designator, found {self.inputSym}')
        self.next()

        while self.inputSym.type == Token.OPENBRACKET:
            self.next()

            self.expression(context)

            self._check_token(Token.CLOSEBRACKET,
                              f'Expecting "]", found {self.inputSym}')
            self.next()

    @_nonterminal
    def factor(self, context: SimpleBB):
        # TODO: simple exampl
        # factor = designator | number | "(" expression ")" | funcCall

        if self.inputSym.type == Token.IDENT:
            self.designator(context)

        elif self.inputSym.type == Token.NUMBER:
            num = self.tokenizer.num
            num_ir = SSA.Const.get_const(num)
            self.next()

        elif self.inputSym.type == Token.OPENPAREN:
            self.next()
            self.expression(context)
            self._check_token(Token.CLOSEPAREN,
                              "Unmatched parentheses in factor!")
            self.next()

        elif self.inputSym.type == Token.CALL:
            self.funcCall(context)

        else:
            raise Exception(
                f"Factor starts with unexpected token {self.inputSym}")

    @_nonterminal
    def term(self, context: SimpleBB):
        # TODO: simple examle
        # term = factor { ("*" | "/") factor}

        self.factor(context)

        while True:
            if self.inputSym.type == Token.TIMES:
                self.next()
                self.factor(context)
            elif self.inputSym.type == Token.DIV:
                self.next()
                self.factor(context)
            else:
                return

    @_nonterminal
    def expression(self, context: SimpleBB):
        # TODO: simple example
        # expression = term {("+" | "-") term}

        self.term(context)

        while True:
            if self.inputSym.type == Token.PLUS:
                self.next()
                self.term(context)
            elif self.inputSym.type == Token.MINUS:
                self.next()
                self.term(context)
            else:
                return

    @_nonterminal
    def relation(self, context: SimpleBB):
        # relation = expression relOp expression

        self.expression(context)

        self._check_tokens(Token.RELOPS, 'Expecting relation operator, found '
                           f'{self.inputSym}')
        self.next()

        self.expression(context)

    @_nonterminal
    def assignment(self, context: SimpleBB):
        # TODO: simple example
        # assignment = "let" designator "<-" expression

        self._check_token(
            Token.LET, f'Expecting keyword "let", found {self.inputSym}')
        self.next()

        self.designator(context)

        self._check_token(Token.BECOMES, 'Expecting "<-" after variable name, '
                          f'found {self.inputSym}')
        self.next()

        self.expression(context)

    @_nonterminal
    def funcCall(self, context: SimpleBB):
        # TODO: simple example > only read and write
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
                self.expression(context)

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
    def ifStatement(self, lastBlock: Block) -> SuperBlock:
        # ifStatement = "if" relation "then" statSequence [ "else" statSequence ] "fi"

        superBlock = SuperBlock("if statement")
        superBlock.last = lastBlock

        relBlock = BranchBB()
        connectBlock = JoinBB()
        relBlock.last = lastBlock
        superBlock.head = relBlock
        superBlock.tail = connectBlock

        self._check_token(Token.IF, 'Expecting "if" at the begining of '
                          f'ifStatement, found {self.inputSym}')
        self.next()
        self.relation()

        self._check_token(Token.THEN, 'Expecting "then" in ifStatement, found '
                          f'{self.inputSym}')
        self.next()
        ifBlock = self.statSequence(relBlock)
        ifBlock = "if body"
        ifBlock.next = connectBlock
        ifBlock.get_lastbb().next = connectBlock
        relBlock.next = ifBlock
        connectBlock.last = ifBlock

        if self.inputSym.type == Token.ELSE:
            self.next()
            elseBlock = self.statSequence(relBlock)
            elseBlock.name = "else body"
            elseBlock.next = connectBlock
            elseBlock.get_lastbb().next = connectBlock
            relBlock.branchBlock = elseBlock
            connectBlock.joiningBlock = elseBlock
        else:
            relBlock.branchBlock = connectBlock
            connectBlock.joiningBlock = relBlock

        self._check_token(Token.FI, 'Expecting "fi" at the end of ifStatement, '
                          f'found {self.inputSym}')
        self.next()

        return superBlock

    @_nonterminal
    def whileStatement(self, lastBlock: Block) -> SuperBlock:
        # whileStatement = "while" relation "do" StatSequence "od"

        superBlock = SuperBlock("while statement")
        superBlock.last = lastBlock

        connectBlock = JoinBB()
        relBlock = BranchBB()
        connectBlock.last = lastBlock
        connectBlock.next = relBlock
        relBlock.last = connectBlock
        superBlock.head = connectBlock
        superBlock.tail = relBlock

        self._check_token(Token.WHILE, 'Expecting "while" at the begining of '
                          f'whileStatement, found {self.inputSym}')
        self.next()
        self.relation()

        self._check_token(Token.DO, 'Expecting "do" in whileStatement, found '
                          f'{self.inputSym}')
        self.next()
        bodyBlock = self.statSequence(relBlock)
        bodyBlock.name = "while body"
        bodyBlock.next = connectBlock
        bodyBlock.get_lastbb().next = connectBlock
        connectBlock.joiningBlock = bodyBlock
        relBlock.next = bodyBlock

        self._check_token(Token.OD, 'Expecting "od" at the end of whileStatement, '
                          f'found {self.inputSym}')
        self.next()

    @_nonterminal
    def returnStatement(self, context: SimpleBB):
        # returnStatement = "return" [ expression ]

        self._check_token(Token.RETURN, 'Expecting "return" at the begining of '
                          f'returnStatement, found {self.inputSym}')
        self.next()

        if self.inputSym.type in [Token.IDENT, Token.NUMBER, Token.OPENPAREN, Token.CALL]:
            self.expression(context)

    def _get_ctx(self, lastBlock: Block, canMerge: bool = False) -> SimpleBB:
        if isinstance(lastBlock, SimpleBB) and canMerge:
            context = lastBlock
        else:
            context = SimpleBB()
            context.last = lastBlock
            lastBlock.next = context
            if isinstance(lastBlock, SuperBlock):
                lastBlock.get_lastbb().next = context
        return context

    @_nonterminal
    def statement(self, lastBlock: Block, canMerge: bool = False) -> Block:
        #  TODO: simple example
        # statement = assignment | funcCall | ifStatement | whileStatement | returnStatement

        if self.inputSym.type == Token.LET:
            context = self._get_ctx(lastBlock, canMerge)
            self.assignment(context)
            return context

        elif self.inputSym.type == Token.CALL:
            context = self._get_ctx(lastBlock, canMerge)
            self.funcCall(context)
            return context

        elif self.inputSym.type == Token.IF:
            ifBlock = self.ifStatement(lastBlock)
            lastBlock.next = ifBlock
            if isinstance(lastBlock, SuperBlock):
                lastBlock.get_lastbb().next = ifBlock
            return ifBlock

        elif self.inputSym.type == Token.WHILE:
            whileBlock = self.whileStatement(lastBlock)
            lastBlock.next = whileBlock
            if isinstance(lastBlock, SuperBlock):
                lastBlock.get_lastbb().next = whileBlock
            return whileBlock

        elif self.inputSym.type == Token.RETURN:
            context = self._get_ctx(lastBlock, canMerge)
            self.returnStatement(context)
            return context

        else:
            raise Exception(f'Expecting statment, found {self.inputSym}')

    @_nonterminal
    def statSequence(self, lastBlock: Block) -> SuperBlock:
        # TODO: simple example
        # statSequence = statement { ";" statement } [ ";" ]

        superBlock = SuperBlock()
        superBlock.last = lastBlock

        statement_tokens = [Token.LET, Token.CALL,
                            Token.IF, Token.WHILE, Token.RETURN]
 
        # Check for the first assignment
        self._check_tokens(statement_tokens,
                           f'Expecting statement, found {self.inputSym}')

        first_block = True
        while self.inputSym.type in statement_tokens:
            block = self.statement(lastBlock, canMerge=not first_block)
            if first_block:
                block.last = lastBlock
                first_block = False

            # Check if a new block was just created
            if block.id != lastBlock.id:
                lastBlock.next = block
                if isinstance(lastBlock, SuperBlock):
                    lastBlock.get_lastbb().next = block

                # Connect new block in the list of the superBlock
                if not superBlock.head:
                    superBlock.head = block
                if superBlock.tail:
                    superBlock.tail.next = block
                    block.last = superBlock.tail
                superBlock.tail = block
                lastBlock = block

            if self.inputSym.type == Token.SEMI:
                self.next()
            else:
                break

        return superBlock

    @_nonterminal
    def typeDecl(self):
        # TODO: simple example
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
    # TODO: Should return a variable table? {variable: type}
    def varDecl(self):
        # TODO: simple example
        # varDecl = typeDecl ident { "," ident } ";"

        # TODO: Get type
        self.typeDecl()

        while True:
            self._check_token(Token.IDENT, 'Expecting identifier, found '
                              f'{self.inputSym}')
            self.inputSym  # TODO: Add to variable table
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
    def funcBody(self) -> SuperBlock:
        # funcBody = { varDecl } "{" [ statSequence ] "}"

        while self.inputSym.type in [Token.VAR, Token.ARR]:
            self.varDecl()

        self._check_token(Token.BEGIN, 'Expecting "{" at the begining of '
                          f'funcBody, found {self.inputSym}')
        self.next()
        
        if self.inputSym.type != Token.END:
            bodyBlock = self.statSequence()
            bodyBlock.name = "function body"

        self._check_token(Token.END, 'Expecting "}" at the end of '
                          f'funcBody, found {self.inputSym}')
        self.next()

    @_nonterminal
    def computation(self) -> SuperBlock:
        # TODO: simple example
        # computation = "main" { varDecl } { funcDecl } "{" statSequence "}" "."

        self._check_token(Token.MAIN, 'Expecting keyword "main" at the start '
                          f'of computation, found {self.inputSym}')
        self.next()

        while self.inputSym.type == Token.VAR or self.inputSym.type == Token.ARR:
            self.varDecl()

        # TODO: Create functions
        while self.inputSym.type == Token.VOID or self.inputSym.type == Token.FUNC:
            self.funcDecl()

        self._check_token(
            Token.BEGIN, f'Expecting "{{", found {self.inputSym}')
        self.next()
        
        # Create const block
        constBlock = SimpleBB()
        mainBlock = self.statSequence(constBlock)
        mainBlock.name = "main function"
        constBlock.next = mainBlock

        self._check_token(
            Token.END, f'Expecting "}}", found {self.inputSym}')
        self.next()

        self._check_token(Token.PERIOD, f'Expecting "." at the end of '
                          f'computation, found {self.inputSym}')
        self.next()

        # Construct computation block that contains the const block ("BB0") and
        # the main block
        self.computationBlock.head = constBlock
        self.computationBlock.tail = mainBlock

        for const_ir in SSA.Const.ALL_CONST:
            constBlock.add_inst(const_ir)

        return


if __name__ == "__main__":
    smplCompiler = SmplCompiler(
        "code_example/code1.smpl", debug=SmplCDebug(file="debug.txt"))
    smplCompiler.computation()
    smplCompiler.debug.dump()

    vis = IRVis()
    vis.block(smplCompiler.computationBlock)
    vis.render()
