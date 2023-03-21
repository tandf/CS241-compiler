from Tokenizer import Tokenizer, Token
from typing import Callable, List, Tuple
from functools import wraps
from Block import *
from SSA import FramePointer, Const, SSAValue, BlockFirstSSA, NextBlockFirstSSA
from Types import *
from Function import *
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
    funcCtx: FuncContext
    mainFuncCtx: FuncContext

    def __init__(self, file: str, debug: SmplCDebug = None):
        self.file = file
        self.debug = debug
        self.tokenizer = Tokenizer(self.file)
        self.inputSym = None
        self.computationBlock = SuperBlock("computation block")
        self.funcCtx = FuncContext()
        self.mainFuncCtx = self.funcCtx

        self._debug_printed = False

        # Read the first token
        self._next()

        # Prevent the user from redefining these functions
        for func, v in PREDEFINED_FUNCTIONS.items():
            id = self.tokenizer.add_name(func)
            v[2] = id  # Set id

    def _next(self) -> None:
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

    def getConst(self, num: int) -> Const:
        return self.funcCtx.getConst(num)

    def vis(self, vis: IRVis) -> None:
        vis.block(self.computationBlock)
        for _, _type in self.funcCtx.identType.items():
            if isinstance(_type, FuncType):
                _type.vis(vis)

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

        # Return values: BaseSSA see below, int: identifier id, bool: is array

        # Returned BaseSSA:
        # For scalars (write=False), return the BaseSSA from the value table.
        # For arrays, first emit instructions to calculate the offset. Then
        # return the address of the element.

        self._check_token(Token.IDENT, 'Expecting identifier at the beginning '
                          f'of designator, found {self.inputSym}')

        sym = self.inputSym
        id = self.tokenizer.id
        if not self.funcCtx.identDefined(id):
            self.error("Using of undefined identifier!")
        _type = self.funcCtx.getIdent(id)

        self._next()

        dims = []
        while self.inputSym.type == Token.OPENBRACKET:
            self._next()

            # Get array dimension(s)
            dim = self.expression(context)
            dims.append(dim)

            self._check_token(Token.CLOSEBRACKET,
                              f'Expecting "]", found {self.inputSym}')
            self._next()

        # Array
        if dims:
            # Compute the offset
            offset = None
            for idx, limit in zip(dims, _type.dims):
                if isinstance(idx, Const):
                    assert idx.num < limit, "Array index out of bound!"
                if offset is not None:
                    offset = SSA.Inst(SSA.OP.MUL, offset,
                                      self.getConst(limit))
                    context.add_inst(offset)
                    offset = SSA.Inst(SSA.OP.ADD, offset, idx)
                    context.add_inst(offset)
                else:
                    offset = idx

            # Scale by 4 (assuming each array element takes 4 bytes)
            offset = SSA.Inst(SSA.OP.MUL, offset, self.getConst(4))
            context.add_inst(offset)

            # Return the SSAValue on the target address
            return offset, id, True

        # Scalar
        else:
            assert _type == VarType.Scalar()
            if write:
                return None, id, False

            else:
                # Trace back and look up for the value in the value table
                value = context.lookup_value_table(id)
                if value is not None:
                    return value, id, False
                else:
                    self.warning("Using uninitialized variable!", sym)
                    zero = self.getConst(0)
                    zero.identifier = id
                    context.get_value_table().set(id, zero)
                    return zero, id, False

    @_nonterminal
    def factor(self, context: SimpleBB) -> SSAValue:
        # factor = designator | number | "(" expression ")" | funcCall

        if self.inputSym.type == Token.IDENT:
            ret, id, is_array = self.designator(context, write=False)
            if is_array:
                # Calculate the element address based on the array's address
                base = context.lookup_value_table(id)
                assert base is not None
                address = SSA.Inst(SSA.OP.ADDA, base, ret)
                context.add_inst(address)

                # Load from the address (ret)
                load = SSA.Inst(SSA.OP.LOAD, address)
                load.identifier = id
                context.add_inst(load)
                return load
            else:
                return ret

        elif self.inputSym.type == Token.NUMBER:
            num = self.tokenizer.num
            ret = self.getConst(num)
            self._next()
            return ret

        elif self.inputSym.type == Token.OPENPAREN:
            self._next()
            ret = self.expression(context)
            self._check_token(Token.CLOSEPAREN,
                              "Unmatched parentheses in factor!")
            self._next()
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
                self._next()
                operand = self.factor(context)
                val = SSA.Inst(SSA.OP.MUL, val, operand)
                context.add_inst(val)

            elif self.inputSym.type == Token.DIV:
                self._next()
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
                self._next()
                operand = self.term(context)
                val = SSA.Inst(SSA.OP.ADD, val, operand)
                context.add_inst(val)

            elif self.inputSym.type == Token.MINUS:
                self._next()
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
        self._next()

        operand2 = self.expression(context)

        ret = SSA.Inst(SSA.OP.CMP, operand1, operand2)
        context.add_inst(ret)

        return ret, relop

    @_nonterminal
    def assignment(self, context: SimpleBB) -> None:
        # assignment = "let" designator "<-" expression

        self._check_token(
            Token.LET, f'Expecting keyword "let", found {self.inputSym}')
        self._next()

        ret, id, is_array = self.designator(context, write=True)

        self._check_token(Token.BECOMES, 'Expecting "<-" after variable name, '
                          f'found {self.inputSym}')
        self._next()

        src = self.expression(context)

        if is_array:
            # Calculate the element address based on the array's address
            base = context.lookup_value_table(id)
            assert base is not None
            address = SSA.Inst(SSA.OP.ADDA, base, ret)
            context.add_inst(address)

            # Store value to array
            store = SSA.Inst(SSA.OP.STORE, src, address)
            store.identifier = id
            context.add_inst(store)

        else:
            # Update the mapping in the value table
            context.get_value_table().set(id, src)

    @_nonterminal
    def funcCall(self, context: SimpleBB) -> SSAValue:
        # funcCall = "call" ident [ "(" [expression { "," expression } ] ")" ]

        self._check_token(Token.CALL, 'Expecting keyword "call" at the '
                          f'begining of funcCall, found {self.inputSym}')
        self._next()

        self._check_token(Token.IDENT, 'Expecting function name, found '
                          f'{self.inputSym}')
        sym = self.inputSym
        id = self.tokenizer.id

        self._next()

        args = []

        if self.inputSym.type == Token.OPENPAREN:
            self._next()

            while self.inputSym.type != Token.CLOSEPAREN:
                args.append(self.expression(context))

                if self.inputSym.type == Token.COMMA:
                    self._next()
                    assert self.inputSym.type != Token.CLOSEPAREN

            self._check_token(Token.CLOSEPAREN, 'Expecting ")", found '
                              f'{self.inputSym}')
            self._next()

        if not self.funcCtx.identDefined(id):
            self.error("Calling undefined function!", sym)

        if sym.sym in PREDEFINED_FUNCTIONS:
            # Emit calling of the predefined function
            op, param_cnt, _ = PREDEFINED_FUNCTIONS[sym.sym]
            if param_cnt != len(args):
                self.error(
                    f"Expecting {param_cnt} parameters, getting {len(args)}.")
            inst = SSA.Inst(op, *args)
            context.add_inst(inst)
            return inst

        else:
            func = self.funcCtx.getIdent(id)
            if not isinstance(func, FuncType):
                self.error(f"Expecting function, getting {func}")
            assert len(func.args) == len(args)
            # Emit call of that function
            call = SSA.CallInst(sym.sym, args)
            context.add_inst(call)
            return call

    @_nonterminal
    def ifStatement(self, lastBlock: Block, superBlock: SuperBlock) -> SuperBlock:
        # ifStatement = "if" relation "then" statSequence [ "else" statSequence ] "fi"

        relBlock = BranchBB()
        connectBlock = JoinBB()
        changed_variables = set()  # The variables changed in either branch
        relBlock.set_prev(lastBlock)
        superBlock.head = relBlock
        superBlock.tail = connectBlock
        connectBlock.last_cs_block = relBlock

        self._check_token(Token.IF, 'Expecting "if" at the begining of '
                          f'ifStatement, found {self.inputSym}')
        self._next()
        rel, relop = self.relation(relBlock)

        self._check_token(Token.THEN, 'Expecting "then" in ifStatement, found '
                          f'{self.inputSym}')
        self._next()
        # Setting up the context
        ifBlock = SuperBlock()
        ifBlock.name = "if body"
        relBlock.set_next(ifBlock)
        connectBlock.set_prev(ifBlock)

        # Process the statement sequence
        self.statSequence(relBlock, ifBlock)
        ifBlock.set_next(connectBlock)
        changed_variables.update(ifBlock.get_value_table().get_ids())
        connectBlock.killStores = set(ifBlock.get_stores())

        # Branch to if block
        ifBraOp = SSA.OP._from_relop(relop)
        conditionBraInst = SSA.Inst(
            ifBraOp, rel, BlockFirstSSA(ifBlock.get_firstbb()))
        relBlock.add_inst(conditionBraInst)

        if self.inputSym.type == Token.ELSE:
            self._next()
            # Setting up the context
            elseBlock = SuperBlock()
            elseBlock.name = "else body"
            relBlock.branchBlock = elseBlock
            connectBlock.joiningBlock = elseBlock
            # Process the statement sequence
            self.statSequence(relBlock, elseBlock)
            elseBlock.set_next(connectBlock)
            changed_variables.update(elseBlock.get_value_table().get_ids())
            connectBlock.killStores = set(elseBlock.get_stores())

            # Branch from the end of else block to connect block
            elseJoinBraOp = SSA.Inst(SSA.OP.BRA, BlockFirstSSA(connectBlock))
            elseBlock.get_lastbb().add_inst(elseJoinBraOp)

        else:
            relBlock.branchBlock = connectBlock
            connectBlock.joiningBlock = relBlock

            # Fall through to connect block
            fallThroughBraInst = SSA.Inst(
                SSA.OP.BRA, BlockFirstSSA(connectBlock))
            relBlock.add_inst(fallThroughBraInst)

        # Add phi instructions
        # 1. Find changed variables: value table from left (else) if any, and
        # from right(if body) branch
        # 2. For each variable, get SSA value from left and right
        # 3. Insert phi(left, right) and update value table
        left_block = connectBlock.joiningBlock
        right_block = connectBlock.prev
        for id in changed_variables:
            id_name = self.tokenizer.id2string(id)
            left = left_block.lookup_value_table(id)
            right = right_block.lookup_value_table(id)

            if left is None:
                self.warning(f"Using uninitialized variable {id_name} in phi!")
                left = self.get_const(0)
            if right is None:
                self.warning(f"Using uninitialized variable {id_name} in phi!")
                right = self.get_const(0)

            if left == right:
                continue

            phi = SSA.Inst(SSA.OP.PHI, left, right)
            phi.identifier = id
            connectBlock.add_inst(phi)
            connectBlock.get_value_table().set(id, phi)

        self._check_token(Token.FI, 'Expecting "fi" at the end of ifStatement, '
                          f'found {self.inputSym}')
        self._next()

        return superBlock

    @_nonterminal
    def whileStatement(self, lastBlock: Block,
                       superBlock: SuperBlock) -> SuperBlock:
        # whileStatement = "while" relation "do" StatSequence "od"

        connectBlock = JoinBB()
        relBlock = BranchBB()
        bodyBlock = SuperBlock()
        bodyBlock.name = "while body"
        connectBlock.joiningBlock = bodyBlock
        connectBlock.set_next(relBlock)
        connectBlock.set_prev(lastBlock)
        relBlock.branchBlock = bodyBlock
        relBlock.set_prev(connectBlock)
        superBlock.head = connectBlock
        superBlock.tail = relBlock

        self._check_token(Token.WHILE, 'Expecting "while" at the begining of '
                          f'whileStatement, found {self.inputSym}')
        self._next()
        rel, relop = self.relation(relBlock)

        self._check_token(Token.DO, 'Expecting "do" in whileStatement, found '
                          f'{self.inputSym}')
        self._next()

        # Process while body
        self.statSequence(relBlock, bodyBlock)
        bodyBlock.set_next(connectBlock)
        changed_variables = bodyBlock.get_value_table().get_ids()
        connectBlock.killStores = set(bodyBlock.get_stores())

        self._check_token(Token.OD, 'Expecting "od" at the end of whileStatement, '
                          f'found {self.inputSym}')
        self._next()

        # Branch from relation block to body block if condition is met
        whileBraOp = SSA.OP._from_relop(relop)
        conditionBraInst = SSA.Inst(
            whileBraOp, rel, BlockFirstSSA(bodyBlock.get_firstbb()))
        relBlock.add_inst(conditionBraInst)

        # Branch from relation block to the next block of while
        relToNextBlockBraInst = SSA.Inst(SSA.OP.BRA, NextBlockFirstSSA(relBlock))
        relBlock.add_inst(relToNextBlockBraInst)

        # Branch from while body to connect block unconditionally
        bodyToJoinBraInst = SSA.Inst(SSA.OP.BRA, BlockFirstSSA(connectBlock))
        bodyBlock.get_lastbb().add_inst(bodyToJoinBraInst)

        # : Add phi instructions
        # 0. Annotate SSA value with variable name in assignments
        # 1. Find changed variables: must from left (while body) branch
        # 2. For each variable, get SSA value from left and right
        # 3. Insert phi(left, right) and update value table
        # 4. Change SSA values used in the rel block and the while body block
        left_block = connectBlock.joiningBlock
        right_block = connectBlock.prev
        for id in changed_variables:
            id_name = self.tokenizer.id2string(id)
            left = left_block.lookup_value_table(id)
            right = right_block.lookup_value_table(id)

            # The changed variable must have been changed in the while body
            assert left is not None
            if right is None:
                self.warning(f"Using uninitialized variable {id_name} in phi!")
                right = self.get_const(0)

            if left == right:
                continue

            phi = SSA.Inst(SSA.OP.PHI, left, right)
            phi.identifier = id
            connectBlock.add_inst(phi)
            connectBlock.get_value_table().set(id, phi)

            # Change SSA values for id in rel block and while body block from
            # original SSA (that from before while, i.e. right) to phi
            relBlock.replace_operand(right, id, phi)
            bodyBlock.replace_operand(right, id, phi)

        return superBlock

    @_nonterminal
    def returnStatement(self, context: SimpleBB) -> SSAValue:
        # returnStatement = "return" [ expression ]

        self._check_token(Token.RETURN, 'Expecting "return" at the begining of '
                          f'returnStatement, found {self.inputSym}')
        self._next()

        if self.inputSym.type in [Token.IDENT, Token.NUMBER, Token.OPENPAREN, Token.CALL]:
            value = self.expression(context)
            ret = SSA.Inst(SSA.OP.RET, value)
        else:
            ret = SSA.Inst(SSA.OP.RET)

        context.add_inst(ret)
        return ret

    def _get_ctx(self, lastBlock: Block, canMerge: bool = False) -> SimpleBB:
        if isinstance(lastBlock, SimpleBB) and canMerge:
            context = lastBlock
        else:
            context = SimpleBB()
            context.set_prev(lastBlock)
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
            ifBlock = SuperBlock("if statement")
            ifBlock.set_prev(lastBlock)
            self.ifStatement(lastBlock, ifBlock)
            return ifBlock

        elif self.inputSym.type == Token.WHILE:
            whileBlock = SuperBlock("while statement")
            whileBlock.set_prev(lastBlock)
            self.whileStatement(lastBlock, whileBlock)
            return whileBlock

        elif self.inputSym.type == Token.RETURN:
            context = self._get_ctx(lastBlock, canMerge)
            self.returnStatement(context)
            return context

        else:
            raise Exception(f'Expecting statment, found {self.inputSym}')

    @_nonterminal
    def statSequence(self, lastBlock: Block, superBlock: SuperBlock):
        # statSequence = statement { ";" statement } [ ";" ]

        superBlock.set_prev(lastBlock)

        statement_tokens = [Token.LET, Token.CALL,
                            Token.IF, Token.WHILE, Token.RETURN]
 
        # Check for the first assignment
        self._check_tokens(statement_tokens,
                           f'Expecting statement, found {self.inputSym}')

        while self.inputSym.type in statement_tokens:
            # This is the first block in the super block
            if superBlock.tail is None:
                block = self.statement(lastBlock, canMerge=False)
                block.set_prev(lastBlock)
                superBlock.head = block
                superBlock.tail = block

            else:
                block = self.statement(superBlock.tail, canMerge=True)
                # Check if a new block was just created
                if block.id != superBlock.tail.id:
                    # Connect new block in the list of the superBlock
                    superBlock.tail.set_next(block)
                    block.set_prev(superBlock.tail)
                    superBlock.tail = block

            if self.inputSym.type == Token.SEMI:
                self._next()
            else:
                break

    @_nonterminal
    def typeDecl(self) -> VarType:
        # typeDecl = "var" | "array" "[" number "]" { "[" number "]" }

        if self.inputSym.type == Token.VAR:
            self._next()
            return VarType.Scalar()

        elif self.inputSym.type == Token.ARR:
            self._next()

            # Check for the first open bracket
            self._check_token(Token.OPENBRACKET,
                              f'Expecting "[", found {self.inputSym}')

            dims = []
            while self.inputSym.type == Token.OPENBRACKET:
                self._next()

                self._check_token(Token.NUMBER,
                                  f'Expecting number, found {self.inputSym}')
                dim = self.tokenizer.num
                dims.append(dim)
                self._next()

                self._check_token(Token.CLOSEBRACKET,
                                  f'Expecting "]", found {self.inputSym}')
                self._next()
            return VarType(dims)

        else:
            raise Exception('Excepting "var" or "array" at the beginning of '
                            f'typeDecl, found {self.inputSym}')

    @_nonterminal
    def varDecl(self, context: SimpleBB):
        # varDecl = typeDecl ident { "," ident } ";"

        # Get type
        _type = self.typeDecl()

        while True:
            self._check_token(Token.IDENT, 'Expecting identifier, found '
                              f'{self.inputSym}')

            # Add identifier to type table
            sym = self.inputSym
            id = self.tokenizer.id
            if self.funcCtx.identDefined(id):
                self.error("Redefinition of variable!", sym)
            self.funcCtx.setIdent(id, _type)

            if _type.is_array():
                fp = FramePointer()
                addr = SSA.Inst(SSA.OP.ADD, fp, self.getConst(fp.offset))
                context.add_inst(addr)
                fp.increment(_type.size())
                context.value_table.set(id, addr)

            self._next()

            if self.inputSym.type == Token.COMMA:
                self._next()
            elif self.inputSym.type == Token.SEMI:
                self._next()
                break
            else:
                raise Exception(f'Excepting "," or ";", found {self.inputSym}')

    @_nonterminal
    def funcDecl(self):
        # funcDecl = [ "void" ] "function" ident formalParam ";" funcBody ";"

        is_void = False

        if self.inputSym.type == Token.VOID:
            self._next()
            is_void = True

        self._check_token(Token.FUNC, 'Expecting keyword "function" at the '
                          f'beginning of funcDecl, found {self.inputSym}')
        self._next()

        self._check_token(Token.IDENT, 'Expecting identifier after keyword '
                          f'"function", found {self.inputSym}')

        # Create function object
        sym = self.inputSym
        id = self.tokenizer.id
        if self.funcCtx.identDefined(id):
            self.error("Redefinition of variable!", sym)
        func = FuncType(sym.sym, is_void)

        # Add functions to the context
        for ident, _type in self.funcCtx.identType.items():
            if isinstance(_type, FuncType):
                func.funcCtx.setIdent(ident, _type)
        self.funcCtx.setIdent(id, func)
        # Set context
        self.funcCtx = func.funcCtx

        self._next()

        self.formalParam(func)

        self._check_token(Token.SEMI, 'Expecting ";" after formalParam, '
                          f'found {self.inputSym}')
        self._next()

        self.funcBody(func.bodyBlock)
        func.bodyBlock.set_next(func.endBlock)
        func.bodyBlock.set_prev(func.constBlock)

        self._check_token(Token.SEMI, 'Expecting ";" after funcBody, '
                          f'found {self.inputSym}')
        self._next()

        # Restore context
        self.funcCtx = self.mainFuncCtx

    @_nonterminal
    def formalParam(self, func: FuncType):
        # formalParam = "(" [ident { "," ident }] ")"

        self._check_token(Token.OPENPAREN, 'Expecting "(" at the begining of '
                          f'formalParam, found {self.inputSym}')
        self._next()
                          
        paramCnt = 0

        while self.inputSym.type == Token.IDENT:
            # Collect all parameters, create an ARG inst for each
            sym = self.inputSym
            id = self.tokenizer.id
            if self.funcCtx.identDefined(id):
                self.error("Redefinition of variable!", sym)
            # Formal parameters are all scalars
            self.funcCtx.setIdent(id, VarType.Scalar())
            arg = SSA.Inst(SSA.OP.ARG, self.getConst(paramCnt))
            func.constBlock.add_inst(arg)
            func.constBlock.get_value_table().set(id, arg)
            func.add_arg(arg)
            paramCnt += 1

            self._next()

            if self.inputSym.type == Token.COMMA:
                self._next()
                self._check_token(Token.IDENT, 'Expecting identifier after '
                                  f'comma, found {self.inputSym}')
            else:
                break

        self._check_token(Token.CLOSEPAREN, 'Expecting ")" at the end of '
                          f'formalParam, found {self.inputSym}')
        self._next()

    @_nonterminal
    def funcBody(self, superBlock: SuperBlock):
        # funcBody = { varDecl } "{" [ statSequence ] "}"

        while self.inputSym.type in [Token.VAR, Token.ARR]:
            self.varDecl(self.funcCtx.constBlock)

        self._check_token(Token.BEGIN, 'Expecting "{" at the begining of '
                          f'funcBody, found {self.inputSym}')
        self._next()
        
        if self.inputSym.type != Token.END:
            self.statSequence(self.funcCtx.constBlock, superBlock)
        else:
            emptyBlock = SimpleBB()
            superBlock.head = emptyBlock
            superBlock.tail = emptyBlock

        self._check_token(Token.END, 'Expecting "}" at the end of '
                          f'funcBody, found {self.inputSym}')
        self._next()

    @_nonterminal
    def computation(self) -> SuperBlock:
        # computation = "main" { varDecl } { funcDecl } "{" statSequence "}" "."

        self._check_token(Token.MAIN, 'Expecting keyword "main" at the start '
                          f'of computation, found {self.inputSym}')
        self._next()

        # Create blocks
        constBlock = SimpleBB()
        endBlock = SimpleBB()
        mainBlock = SuperBlock("main function")
        self.funcCtx.constBlock = constBlock

        SSA.Const.constBlock = constBlock
        constBlock.add_inst(FramePointer())
        constBlock.set_prev(constBlock)  # To itself, meaning the first
        constBlock.set_next(mainBlock)
        endBlock.set_prev(mainBlock)
        endBlock.set_next(endBlock)  # To itself, meaning the last

        # Construct computation block that contains the const block ("BB0") and
        # the main block
        self.computationBlock.head = constBlock
        self.computationBlock.tail = endBlock

        while self.inputSym.type == Token.VAR or self.inputSym.type == Token.ARR:
            self.varDecl(self.funcCtx.constBlock)

        # Create functions
        while self.inputSym.type == Token.VOID or self.inputSym.type == Token.FUNC:
            self.funcDecl()

        self._check_token(
            Token.BEGIN, 'Expecting "{", found ' + f'{self.inputSym}')
        self._next()
        
        # Process the statement sequence
        self.statSequence(constBlock, mainBlock)
        mainBlock.set_next(endBlock)
        endBlock.add_inst(SSA.Inst(SSA.OP.END))

        self._check_token(
            Token.END, 'Expecting "}", found ' + f'{self.inputSym}')
        self._next()

        self._check_token(Token.PERIOD, f'Expecting "." at the end of '
                          f'computation, found {self.inputSym}')
        self._next()

        # Regenerate all common subexpressions in the end. Previously some cs
        # can be falsely generated because the graph is not complete.
        for inst in SSA.SSAValue.ALL_SSA:
            if isinstance(inst, SSA.Inst):
                inst._get_cs_flag = False
