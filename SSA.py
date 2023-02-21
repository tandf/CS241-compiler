from __future__ import annotations
from enum import Enum, auto
from typing import List
import Tokenizer


class SSAValue:
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
    def get_inst(cls, id: int) -> SSAValue:
        return cls.ALL_SSA[id]

    def __init__(self):
        # Unique id for each SSA instruction
        self.id = SSAValue.CNT
        # Update class variables
        SSAValue.CNT += 1
        SSAValue.ALL_SSA.append(self)

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, __o: Inst) -> bool:
        return __o and self.id == __o.id


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

    def to_str(self, dot_style: bool = False) -> str:
        s= f'<font color="#FF69B4"><b>{self.id}</b></font>' if dot_style else f"{self.id}"
        s += f": const #{self.num}"
        return s

    def __str__(self) -> str:
        return self.to_str(dot_style=False)

    @classmethod
    def get_const(cls, num) -> Const:
        for const in cls.ALL_CONST:
            if const.num == num:
                return const
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

    _RELOP_TABLE = {
        Tokenizer.Token.EQL: BEQ,
        Tokenizer.Token.NEQ: BNE,
        Tokenizer.Token.LSS: BLT,
        Tokenizer.Token.GEQ: BGE,
        Tokenizer.Token.LEQ: BLE,
        Tokenizer.Token.GTR: BGT,
    }

    def __str__(self) -> str:
        return f'{self.name}'.lower()

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def _from_relop(cls, relop: int) -> OP:
        return

class Inst(SSAValue):
    op: OP
    x: Inst
    y: Inst
    x_ident: int
    y_ident: int
    common_subexpression: Inst
    op_last_inst: Inst

    def __init__(self, op: OP, x: Inst = None, y: Inst = None,
                 x_ident: int = None, y_ident: int = None,
                 op_last_inst: Inst = None):
        super().__init__()

        self.op = op
        self.x = x
        self.y = y
        self.x_ident = x_ident
        self.y_ident = y_ident
        self.common_subexpression = None
        # Last SSA instruction with the same op
        self.op_last_inst = op_last_inst

    def to_str(self, dot_style: bool = False) -> str:
        s = f'<font color="#FF69B4"><b>{self.id}</b></font>' if dot_style else f"{self.id}"
        s += f": {self.op}"
        if self.x:
            s += f" ({self.x.id})"
        if self.y:
            s += f" ({self.y.id})"
        if self.common_subexpression:
            s += f" (cs: {self.common_subexpression.id})"
        return s

    def __str__(self) -> str:
        return self.to_str(dot_style=False)

    def is_common_subexpression(self, __o: Inst,
                                commutative: bool = False) -> bool:
        if self.op != __o.op:
            return False
        if self.x == __o.x and self.y == __o.y:
            return True
        elif commutative and self.x == __o.y and self.y == __o.x:
            return True
        return False

    def replace_operand(self, _from: Inst, _from_ident: int, _to: Inst) -> None:
        if self.x == _from and self.x_ident == _from_ident:
            self.x = _to
        if self.y == _from and self.y_ident == _from_ident:
            self.y = _to
