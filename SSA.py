from __future__ import annotations
from enum import Enum, auto
from typing import List
import Tokenizer
import copy


class BaseSSA:
    id: int

    # Global count of all instructions
    CNT = 0
    # A list of all SSA instructions, ordered by id
    ALL_SSA = []

    @classmethod
    def _init(cls) -> None:
        # For unit test
        cls.CNT = 0
        cls.ALL_SSA = []

    @classmethod
    def get_inst(cls, id: int) -> BaseSSA:
        return cls.ALL_SSA[id]

    def __init__(self):
        # Unique id for each SSA instruction
        self.id = BaseSSA.CNT
        # Update class variables
        BaseSSA.CNT += 1
        BaseSSA.ALL_SSA.append(self)

    # Get the real id for the SSA value. For meta SSA, return the *real* id of
    # the SSA pointed to; for cse, return the real id of the SSA that is the
    # common subexpression
    def get_id(self) -> int:
        return self.id

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, __o: BaseSSA) -> bool:
        return __o and self.get_id() == __o.get_id()


class SSAValue(BaseSSA):
    identifier: int

    def __init__(self):
        super().__init__()
        # The corresponding identifier. The same SSA value (SSA id) can map to
        # multiple identifier, and the same identifier can map to multiple SSA
        # value (at different time).
        # This mapping is for changing the SSA value which is required for
        # inserting phi in while blocks
        self.identifier = None


class Const(SSAValue):
    ALL_CONST: List[Const]

    # A list of all defined const values
    ALL_CONST = []

    @classmethod
    def _init(cls) -> None:
        # For unit test
        cls.ALL_CONST = []

    def __init__(self, num: int):
        super().__init__()
        self.num = num
        Const.ALL_CONST.append(self)

    def to_str(self, dot_style: bool = False, color: str = "black") -> str:
        s = f'<font color="{color}"><b>{self.get_id()}</b></font>' \
            if dot_style else f"{self.get_id()}"
        s += f": const #{self.num}"
        return s

    def __str__(self) -> str:
        return self.to_str(dot_style=False)

    @classmethod
    def get_const(cls, num) -> Const:
        for const in cls.ALL_CONST:
            if const.num == num:
                return copy.deepcopy(const)
        return Const(num)


class OP(Enum):
    EMPTY = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    CMP = auto()

    ADDA = auto()
    LOAD = auto()
    STORE = auto()
    PHI = auto()

    END = auto()
    BRA = auto()
    BNE = auto()
    BEQ = auto()
    BLE = auto()
    BLT = auto()
    BGE = auto()
    BGT = auto()

    READ = auto()
    WRITE = auto()
    WRITENL = auto()

    # Custom inst
    NOP = auto()

    def __str__(self) -> str:
        return f'{self.name}'.lower()

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def _from_relop(cls, relop: int) -> OP:
        _RELOP_TABLE = {
            Tokenizer.Token.EQL: cls.BEQ,
            Tokenizer.Token.NEQ: cls.BNE,
            Tokenizer.Token.LSS: cls.BLT,
            Tokenizer.Token.GEQ: cls.BGE,
            Tokenizer.Token.LEQ: cls.BLE,
            Tokenizer.Token.GTR: cls.BGT,
        }

        assert relop in _RELOP_TABLE
        return _RELOP_TABLE[relop]

    def is_commutative(self) -> bool:
        return self in OP.COMMUTATIVE_OP


OP.COMMUTATIVE_OP = {OP.ADD, OP.MUL}
OP.IO_OP = {OP.READ, OP.WRITE, OP.WRITENL}
OP.BRANCH_OP = {OP.BRA, OP.BNE, OP.BEQ, OP.BLE, OP.BLT, OP.BGE, OP.BGT}


class Inst(SSAValue):
    op: OP
    x: BaseSSA
    y: BaseSSA
    op_last_inst: Inst

    def __init__(self, op: OP, x: Inst = None, y: Inst = None,
                 op_last_inst: Inst = None):
        super().__init__()

        self.op = op
        self.x = x
        self.y = y
        # Last SSA instruction with the same op
        self.op_last_inst = op_last_inst

    def to_str(self, dot_style: bool = False, color: str = "black") -> str:
        s = f'<font color="{color}"><b>{self.get_id(cse=False)}</b></font>' \
            if dot_style else f"{self.get_id()}"
        s += f": {self.op}"
        if self.x:
            s += f" ({self.x.get_id()})"
        if self.y:
            s += f" ({self.y.get_id()})"
        #  s += f" (last: {self.op_last_inst.get_id() if self.op_last_inst else 'None'})"
        cs = self.get_cs()
        if cs:
            s += f' <font color="red">[cs: {cs.get_id()}]</font>' \
                if dot_style else f' [cs: {cs.get_id()}]'
        return s

    def __str__(self) -> str:
        return self.to_str(dot_style=False)

    def is_common_subexpression(self, __o: Inst) -> bool:
        if self.op != __o.op:
            return False
        if self.x == __o.x and self.y == __o.y:
            return True
        elif self.op.is_commutative() and self.x == __o.y and self.y == __o.x:
            return True
        return False

    def get_cs(self) -> Inst:
        inst = self.op_last_inst
        while inst is not None:
            if self.is_common_subexpression(inst):
                return inst
            inst = inst.op_last_inst
        return None

    def replace_operand(self, _from: Inst, _from_ident: int, _to: Inst) -> None:
        if self.x is not None and isinstance(self.x, SSAValue) and \
                self.x == _from and self.x.identifier == _from_ident:
            self.x = _to
        if self.y is not None and isinstance(self.y, SSAValue) and \
                self.y == _from and self.y.identifier == _from_ident:
            self.y = _to

    def get_id(self, cse: bool = True) -> int:
        if cse and self.get_cs() is not None:
            return self.get_cs().get_id()
        else:
            return super().get_id()


class MetaSSA(BaseSSA):
    # Sometimes we cannot get a specific SSA instruction, but want to get the
    # first, the last, or the next instruction. This class is used to model such
    # behaviors.

    def __init__(self, block):
        self.block = block

    def get_target_SSA(self) -> BaseSSA:
        raise Exception("Unimplemented!")

    def get_id(self) -> int:
        targetSSA = self.get_target_SSA()
        assert targetSSA is not None
        return targetSSA.get_id()


class BlockFirstSSA(MetaSSA):
    def __init__(self, block):
        super().__init__(block)

    def get_target_SSA(self) -> BaseSSA:
        assert self.block is not None
        targetSSA =  self.block.get_first_inst()
        if targetSSA is None:
            targetSSA = self.block.add_nop()
        return targetSSA


class NextBlockFirstSSA(MetaSSA):
    def __init__(self, block):
        super().__init__(block)

    def get_target_SSA(self) -> BaseSSA:
        assert self.block is not None
        assert self.block.next is not None
        targetSSA =  self.block.next.get_first_inst()
        if targetSSA is None:
            targetSSA = self.block.next.add_nop()
        return targetSSA

