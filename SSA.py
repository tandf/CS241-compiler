from __future__ import annotations
from enum import Enum, auto
from typing import List


class SSAValue:
    id: int

    # Global count of all instructions
    CNT = 0
    # A list of all SSA instructions, ordered by id
    ALL_INST = []

    @classmethod
    def _init(cls) -> None:
        # For unit test
        cls.CNT = 0
        cls.ALL_INST = []

    @classmethod
    def get_inst(cls, id: int) -> SSAValue:
        return cls.ALL_INST[id]

    def __init__(self):
        # Unique id for each SSA instruction
        self.id = SSAValue.CNT
        # Update class variables
        SSAValue.CNT += 1
        SSAValue.ALL_INST.append(self)

    def __eq__(self, __o: Inst) -> bool:
        return __o and self.id == __o.id


class Const(SSAValue):
    ALL_CONST: List[Const]

    # A list of all defined const values
    ALL_CONST = []

    def __init__(self, num: int):
        super().__init__()
        self.num = num
        Const.ALL_CONST.append(self)

    def __str__(self) -> str:
        s = f"{self.id} # {self.num}"
        return s

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def get_const(cls, num) -> Const:
        for const in cls.ALL_CONST:
            if const.num == num:
                return const
        return Const(num)


class OP(Enum):
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

    def __str__(self) -> str:
        return f'{self.name}'

    def __repr__(self) -> str:
        return self.__str__()

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

    def __str__(self) -> str:
        s = f"{self.id} {str(self.op)}"
        if self.x:
            s += f" {self.x.id}"
        if self.y:
            s += f" {self.y.id}"
        if self.common_subexpression:
            s += f" (cs: {self.common_subexpression.id})"
        return s

    def __repr__(self) -> str:
        return self.__str__()

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
