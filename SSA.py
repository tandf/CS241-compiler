from __future__ import annotations
from enum import Enum

class OP(Enum):
    ADD = 0
    SUB = 1
    MUL = 2
    DIV = 3
    CMP = 4

    ADDA = 5
    LOAD = 6
    STORE = 7
    PHI = 8

    END = 9
    BRA = 10
    BNE = 11
    BEQ = 12
    BLE = 13
    BLT = 14
    BGE = 15
    BGT = 16

    READ = 17
    WRITE = 18
    WRITENL = 19


class Inst:
    op: OP
    x: Inst
    y: Inst
    x_ident: int
    y_ident: int
    common_subexpression: Inst
    op_last_inst: Inst

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
    def get_inst(cls, id: int) -> Inst:
        return cls.ALL_INST[id]

    def __init__(self, op: OP, x: Inst = None, y: Inst = None,
                 x_ident: int = None, y_ident: int = None,
                 op_last_inst: Inst = None):
        self.op = op
        self.x = x
        self.y = y
        self.x_ident = x_ident
        self.y_ident = y_ident
        self.common_subexpression = None

        # Unique id for each SSA instruction
        self.id = Inst.CNT
        # Last SSA instruction with the same op
        self.op_last_inst = op_last_inst

        # Update class variables
        Inst.CNT += 1
        Inst.ALL_INST.append(self)

    def __eq__(self, __o: Inst) -> bool:
        return __o and self.id == __o.id

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
