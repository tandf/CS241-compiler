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
    last_op: Inst

    # Global count of all instructions
    CNT = 0
    # A list of all SSA instructions, ordered by id
    ALL_INST = []

    @classmethod
    def get_inst(cls, id: int) -> Inst:
        return cls.ALL_INST[id]

    def __init__(self, op: int, x: Inst = None, y: Inst = None,
                 last_inst: Inst = None, deleted: bool = False):
        self.op = op
        self.x = x
        self.y = y
        self.deleted = deleted

        # Unique id for each SSA instruction
        self.id = Inst.CNT
        # Last SSA instruction with the same op
        self.last_inst = last_inst

        # Update class variables
        Inst.CNT += 1
        Inst.ALL_INST.append(self)

    def __eq__(self, __o: Inst) -> bool:
        return self.id == __o.id
