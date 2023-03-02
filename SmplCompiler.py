from Tokenizer import Tokenizer, Token
from typing import Callable, List, Tuple
from functools import wraps
from Block import *
from IRVis import IRVis
from SSA import SSAValue, Const, Inst, BlockFirstSSA
from Types import *
from Function import Function


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

    variable_types: Dict[int, VarType]

    def __init__(self, file: str, debug: SmplCDebug = None):
        self.file = file
        self.debug = debug
        self.tokenizer = Tokenizer(self.file)
        self.inputSym = None
        self.computationBlock = SuperBlock("computation block")

        # Variables and their types
        self.variable_types = {}  # Identifier id : var type
        # Functions and their definition super block
        self.funcs = {}  # Identifier id : function

        self._debug_printed = False

        # Read the first token
        self.next()

        # Prevent the user from redefining these functions
        for func in Function.PREDEFINED_FUNCTIONS:
            self.tokenizer.add_name(func)

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
            try:
                print(self.inputSym.source_loc())
            except:
                pass
            self._debug_printed = True

    def _compiling_msg(self, msg: str, sym: Token = None) -> str:
        sym = sym if sym else self.inputSym
        return f"{sym.source_loc()}\n{msg}"

    def warning(self, msg:str, sym:Token = None) -> None:
        print(self._compiling_msg("WARNING: " + msg, sym))

    def error(self, msg: str, sym: Token = None) -> None:
        raise Exception(self._compiling_msg("ERROR: " + msg, sym))

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
    def designator(self, context: SimpleBB,
                   write: bool) -> Tuple[SSAValue, int, bool]:
        # designator = ident{ "[" expression "]" }

        # Return values: SSAValue see below, int: identifier id, bool: is array

        # Returned SSAValue:
        # For scalars (write=False), return the SSAValue from the value table.
        # For arrays, first emit instructions to calculate the offset. Then
        # return the SSAValue of the offset.

        self._check_token(Token.IDENT, 'Expecting identifier at the beginning '
                          f'of designator, found {self.inputSym}')

        sym = self.inputSym
        id = self.tokenizer.id
        type = self.variable_types[id]

        self.next()

        dims = []
        while self.inputSym.type == Token.OPENBRACKET:
            self.next()

            # TODO: Get array dimension(s) and combine them based on the
            # variable type
            dim = self.expression(context)
            dims.append(dim)

            self._check_token(Token.CLOSEBRACKET,
                              f'Expecting "]", found {self.inputSym}')
            self.next()

        # Array
        if dims:
            # TODO: Deal with array
            # 1. Compute the offset
            # 2. Return the SSAValue for the offset
            return None, id, True

        # Scalar
        else:
            assert type == VarType.Scalar()
            if write:
                return None, id, False

            else:
                # Trace back and look up for the value in the value table
                value = context.lookup_value_table(id)
                if value is not None:
                    return value, id, False
                else:
                    self.warning("Using uninitialized variable!", sym)
                    zero = SSA.Const.get_const(0)
                    context.get_value_table().set(id, zero)
                    return zero, id, False

    @_nonterminal
    def factor(self, context: SimpleBB) -> SSAValue:
        # factor = designator | number | "(" expression ")" | funcCall

        if self.inputSym.type == Token.IDENT:
            ret, id, is_array = self.designator(context, write=False)
            if is_array:
                # TODO: Load from the offset (ret)
                pass
            else:
                return ret

        elif self.inputSym.type == Token.NUMBER:
            num = self.tokenizer.num
            ret = Const.get_const(num)
            self.next()
            return ret

        elif self.inputSym.type == Token.OPENPAREN:
            self.next()
            ret = self.expression(context)
            self._check_token(Token.CLOSEPAREN,
                              "Unmatched parentheses in factor!")
            self.next()
            return ret

        elif self.inputSym.type == Token.CALL:
            return self.funcCall(context)

        else:
            raise Exception(
                f"Factor starts with unexpected token {self.inputSym}")

    @_nonterminal
    def term(self, context: SimpleBB) -> SSAValue:
        # term = factor { ("*" | "/") factor}

        val = self.factor(context)

        while True:
            if self.inputSym.type == Token.TIMES:
                self.next()
                operand = self.factor(context)
                val = SSA.Inst(SSA.OP.MUL, val, operand)
                context.add_inst(val)

            elif self.inputSym.type == Token.DIV:
                self.next()
                operand = self.factor(context)
                val = SSA.Inst(SSA.OP.DIV, val, operand)
                context.add_inst(val)

            else:
                return val

    @_nonterminal
    def expression(self, context: SimpleBB) -> SSAValue:
        # expression = term {("+" | "-") term}

        val = self.term(context)

        while True:
            if self.inputSym.type == Token.PLUS:
                self.next()
                operand = self.term(context)
                val = SSA.Inst(SSA.OP.ADD, val, operand)
                context.add_inst(val)

            elif self.inputSym.type == Token.MINUS:
                self.next()
                operand = self.term(context)
                val = SSA.Inst(SSA.OP.SUB, val, operand)
                context.add_inst(val)

            else:
                return val

    @_nonterminal
    def relation(self, context: SimpleBB) -> Tuple[SSAValue, int]:
        # relation = expression relOp expression

        operand1 = self.expression(context)

        self._check_tokens(Token.RELOPS, 'Expecting relation operator, found '
                           f'{self.inputSym}')
        relop = self.inputSym.type
        self.next()

        operand2 = self.expression(context)

        ret = SSA.Inst(SSA.OP.CMP, operand1, operand2)
        context.add_inst(ret)

        return ret, relop

    @_nonterminal
    def assignment(self, context: SimpleBB) -> None:
        # assignment = "let" designator "<-" expression

        self._check_token(
            Token.LET, f'Expecting keyword "let", found {self.inputSym}')
        self.next()

        dst, id, is_array = self.designator(context, write=True)

        self._check_token(Token.BECOMES, 'Expecting "<-" after variable name, '
                          f'found {self.inputSym}')
        self.next()

        src = self.expression(context)

        if is_array:
            # TODO: Store value to array
            pass
        else:
            # Update the mapping in the value table
            context.get_value_table().set(id, src)

    @_nonterminal
    def funcCall(self, context: SimpleBB) -> SSAValue:
        # funcCall = "call" ident [ "(" [expression { "," expression } ] ")" ]

        self._check_token(Token.CALL, 'Expecting keyword "call" at the '
                          f'begining of funcCall, found {self.inputSym}')
        self.next()

        self._check_token(Token.IDENT, 'Expecting function name, found '
                          f'{self.inputSym}')
        sym = self.inputSym
        id = self.tokenizer.id

        self.next()

        args = []

        if self.inputSym.type == Token.OPENPAREN:
            self.next()

            while self.inputSym.type != Token.CLOSEPAREN:
                args.append(self.expression(context))

                if self.inputSym.type == Token.COMMA:
                    self.next()
                    assert self.inputSym.type != Token.CLOSEPAREN

            self._check_token(Token.CLOSEPAREN, 'Expecting ")", found '
                              f'{self.inputSym}')
            self.next()

        if sym.sym in Function.PREDEFINED_FUNCTIONS:
            # Emit calling of the predefined function
            op, param_cnt = Function.PREDEFINED_FUNCTIONS[sym.sym]
            if param_cnt != len(args):
                self.error(
                    f"Expecting {param_cnt} parameters, getting {len(args)}.")
            inst = SSA.Inst(op, *args)
            context.add_inst(inst)
            return inst

        elif id in self.funcs:
            # TODO: emit calling of that function
            pass

        else:
            self.error("Calling undefined function!", sym)

    @_nonterminal
    def ifStatement(self, lastBlock: Block) -> SuperBlock:
        # ifStatement = "if" relation "then" statSequence [ "else" statSequence ] "fi"

        superBlock = SuperBlock("if statement")
        superBlock.set_last(lastBlock)

        relBlock = BranchBB()
        connectBlock = JoinBB()
        relBlock.set_last(lastBlock)
        superBlock.head = relBlock
        superBlock.tail = connectBlock

        self._check_token(Token.IF, 'Expecting "if" at the begining of '
                          f'ifStatement, found {self.inputSym}')
        self.next()
        rel, relop = self.relation(relBlock)

        self._check_token(Token.THEN, 'Expecting "then" in ifStatement, found '
                          f'{self.inputSym}')
        self.next()
        ifBlock = self.statSequence(relBlock)
        ifBlock.name = "if body"
        ifBlock.set_next(connectBlock)
        relBlock.set_next(ifBlock)
        connectBlock.set_last(ifBlock)

        # Branch to if block
        ifBraOp = SSA.OP._from_relop(relop)
        conditionBraOp = SSA.Inst(
            ifBraOp, rel, BlockFirstSSA(ifBlock.get_firstbb()))
        relBlock.add_inst(conditionBraOp)

        if self.inputSym.type == Token.ELSE:
            self.next()
            elseBlock = self.statSequence(relBlock)
            elseBlock.name = "else body"
            elseBlock.set_next(connectBlock)
            relBlock.branchBlock = elseBlock
            connectBlock.joiningBlock = elseBlock

            # Fall through to else block
            fallThroughBraOp = SSA.Inst(
                SSA.OP.BRA, rel, BlockFirstSSA(elseBlock.get_firstbb()))
            relBlock.add_inst(fallThroughBraOp)
            # Branch from the end of if block to connect block
            ifJoinBraOp = SSA.Inst(SSA.OP.BRA, BlockFirstSSA(connectBlock))
            ifBlock.get_lastbb().add_inst(ifJoinBraOp)

        else:
            relBlock.branchBlock = connectBlock
            connectBlock.joiningBlock = relBlock
            # Fall through to connect block
            fallThroughBraOp = SSA.Inst(
                SSA.OP.BRA, BlockFirstSSA(connectBlock))
            relBlock.add_inst(fallThroughBraOp)

        self._check_token(Token.FI, 'Expecting "fi" at the end of ifStatement, '
                          f'found {self.inputSym}')
        self.next()

        return superBlock

    @_nonterminal
    def whileStatement(self, lastBlock: Block) -> SuperBlock:
        # whileStatement = "while" relation "do" StatSequence "od"

        superBlock = SuperBlock("while statement")
        superBlock.set_last(lastBlock)

        connectBlock = JoinBB()
        relBlock = BranchBB()
        connectBlock.set_last(lastBlock)
        connectBlock.set_next(relBlock)
        relBlock.set_last(connectBlock)
        superBlock.head = connectBlock
        superBlock.tail = relBlock

        self._check_token(Token.WHILE, 'Expecting "while" at the begining of '
                          f'whileStatement, found {self.inputSym}')
        self.next()
        rel, relop = self.relation(relBlock)
        # TODO: add branching inst

        self._check_token(Token.DO, 'Expecting "do" in whileStatement, found '
                          f'{self.inputSym}')
        self.next()
        bodyBlock = self.statSequence(relBlock)
        bodyBlock.name = "while body"
        bodyBlock.set_next(connectBlock)
        connectBlock.joiningBlock = bodyBlock
        relBlock.set_next(bodyBlock)

        self._check_token(Token.OD, 'Expecting "od" at the end of whileStatement, '
                          f'found {self.inputSym}')
        self.next()

    @_nonterminal
    def returnStatement(self, context: SimpleBB) -> SSAValue:
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
            context.set_last(lastBlock)
        return context

    @_nonterminal
    def statement(self, lastBlock: Block, canMerge: bool = False) -> Block:
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
            return ifBlock

        elif self.inputSym.type == Token.WHILE:
            whileBlock = self.whileStatement(lastBlock)
            return whileBlock

        elif self.inputSym.type == Token.RETURN:
            context = self._get_ctx(lastBlock, canMerge)
            self.returnStatement(context)
            return context

        else:
            raise Exception(f'Expecting statment, found {self.inputSym}')

    @_nonterminal
    def statSequence(self, lastBlock: Block) -> SuperBlock:
        # statSequence = statement { ";" statement } [ ";" ]

        superBlock = SuperBlock()
        superBlock.set_last(lastBlock)

        statement_tokens = [Token.LET, Token.CALL,
                            Token.IF, Token.WHILE, Token.RETURN]
 
        # Check for the first assignment
        self._check_tokens(statement_tokens,
                           f'Expecting statement, found {self.inputSym}')

        while self.inputSym.type in statement_tokens:
            # This is the first block in the super block
            if not superBlock.tail:
                block = self.statement(lastBlock, canMerge=False)
                block.set_last(lastBlock)
                superBlock.head = block
                superBlock.tail = block

            else:
                block = self.statement(superBlock.tail, canMerge=True)
                # Check if a new block was just created
                if block.id != superBlock.tail.id:
                    # Connect new block in the list of the superBlock
                    superBlock.tail.set_next(block)
                    block.set_last(superBlock.tail)
                    superBlock.tail = block

            if self.inputSym.type == Token.SEMI:
                self.next()
            else:
                break

        return superBlock

    @_nonterminal
    def typeDecl(self) -> VarType:
        # typeDecl = "var" | "array" "[" number "]" { "[" number "]" }

        if self.inputSym.type == Token.VAR:
            self.next()
            return VarType.Scalar()

        elif self.inputSym.type == Token.ARR:
            self.next()

            # Check for the first open bracket
            self._check_token(Token.OPENBRACKET,
                              f'Expecting "[", found {self.inputSym}')

            dims = []
            while self.inputSym.type == Token.OPENBRACKET:
                self.next()

                self._check_token(Token.NUMBER,
                                  f'Expecting number, found {self.inputSym}')
                dim = self.tokenizer.num
                dims.append(dim)
                self.next()

                self._check_token(Token.CLOSEBRACKET,
                                  f'Expecting "]", found {self.inputSym}')
                self.next()
            return VarType(dims)

        else:
            raise Exception('Excepting "var" or "array" at the beginning of '
                            f'typeDecl, found {self.inputSym}')

    @_nonterminal
    def varDecl(self):
        # varDecl = typeDecl ident { "," ident } ";"

        # Get type
        type = self.typeDecl()

        while True:
            self._check_token(Token.IDENT, 'Expecting identifier, found '
                              f'{self.inputSym}')

            # Add identifier to type table
            sym = self.inputSym
            id = self.tokenizer.id
            if id in self.variable_types:
                self.error("Redefinition of variable!", sym)
            self.variable_types[id] = type

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
        
        constBlock = SimpleBB()

        if self.inputSym.type != Token.END:
            bodyBlock = self.statSequence(constBlock)
            bodyBlock.name = "function body"

        self._check_token(Token.END, 'Expecting "}" at the end of '
                          f'funcBody, found {self.inputSym}')
        self.next()

    @_nonterminal
    def computation(self) -> SuperBlock:
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
        constBlock.set_next(mainBlock)

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

