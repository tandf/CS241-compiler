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
        # The basic block that this inst belongs to
        self.bb = None
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

    def __hash__(self) -> int:
        return self.id


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


class FramePointer(SSAValue):
    offset: int

    _instance = None
    _initialized = False

    def __new__(cls) -> FramePointer:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not FramePointer._initialized:
            super().__init__()
            self.offset = 0
        FramePointer._initialized = True

    def __str__(self) -> str:
        return self.to_str(dot_style=False)

    def increment(self, offset: int) -> None:
        self.offset += offset

    def to_str(self, dot_style: bool = False, color: str = "black") -> str:
        s = f'<font color="{color}"><b>{self.get_id()}</b></font>' \
            if dot_style else f"{self.get_id()}"
        s += f": FP"
        return s


class Const(SSAValue):
    def __init__(self, num: int):
        super().__init__()
        self.num = num

    def to_str(self, dot_style: bool = False, color: str = "black") -> str:
        s = f'<font color="{color}"><b>{self.get_id()}</b></font>' \
            if dot_style else f"{self.get_id()}"
        s += f": const #{self.num}"
        return s

    def __str__(self) -> str:
        return self.to_str(dot_style=False)


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
    # Function call related
    CALL = auto()
    ARG = auto()
    RET = auto()

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
OP.MEM_OP = {OP.LOAD, OP.STORE}
OP.FUNC_OP = {OP.CALL, OP.ARG, OP.RET}


class Inst(SSAValue):
    op: OP
    x: BaseSSA
    y: BaseSSA
    op_last_inst: Inst
    cs: Inst
    _get_cs_flag: bool

    def __init__(self, op: OP, x: BaseSSA = None, y: BaseSSA = None):
        super().__init__()
        assert x is None or isinstance(x, BaseSSA)
        assert y is None or isinstance(y, BaseSSA)

        self.op = op
        self.x = x
        self.y = y
        # Last SSA instruction with the same op
        self.op_last_inst = None
        self.cs = None
        self._get_cs_flag = False

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

    def is_common_subexpression(self, __o: SSAValue) -> bool:
        if not isinstance(__o, Inst):
            return False
        if self.op != __o.op:
            return False
        if self.x == __o.x and self.y == __o.y:
            return True
        elif self.op.is_commutative() and self.x == __o.y and self.y == __o.x:
            return True
        # TODO: For loads, if one value is stored at the same position, we can
        # also use it.
        return False

    def is_cs_kill(self, __o) -> bool:
        if isinstance(__o, SSAValue):
            if not isinstance(__o, Inst):
                return False
            if self.op not in OP.MEM_OP or __o.op != OP.STORE:
                return False
            if __o.get_cs():
                # The instruction will be killed, probably because of another
                # existing store instruction. Skip this one.
                return False
            return self.identifier == __o.identifier
        elif hasattr(__o, "__iter__"):
            for ssa in __o:
                if self.is_cs_kill(ssa):
                    return True
        else:
            raise Exception(f"Can only use is_cs_kill with SSAValue or a list "
                            f"of SSAValue, but received {type(__o)}")

    def get_cs(self) -> Inst:
        if not self._get_cs_flag:
            self.cs = None
            self._get_cs_flag = True

            # Try to find the common subexpression within the same block
            inst = self.op_last_inst
            while inst is not None:
                if self.is_common_subexpression(inst):
                    self.cs = inst
                    return self.cs
                if self.is_cs_kill(inst):
                    return None
                inst = inst.op_last_inst

            # Try to find the common subexpression from previous blocks
            if self.cs is None:
                inst = None
                bb = self.bb
                assert bb is not None, f"Cannot find basic block for {self}"
                while True:
                    # Check the kill store instructions for early kill
                    if self.op in OP.MEM_OP:
                        if self.is_cs_kill(bb.killStores):
                            return None

                    # Move to the next block
                    bb = bb.get_prev_cs_bb()
                    if bb is None:
                        return None

                    # Traverse the linked list for common subexpression
                    inst = bb.cs_table_get(self.op)
                    while inst is not None:
                        if self.is_common_subexpression(inst):
                            self.cs = inst
                            return self.cs
                        if self.is_cs_kill(inst):
                            return None
                        inst = inst.op_last_inst

        return self.cs

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

class CallInst(Inst):
    func_name: str
    call_args: List[SSAValue]

    def __init__(self, func_name: str, args: List[SSAValue]):
        super().__init__(OP.CALL)
        self.func_name = func_name
        self.call_args = args

    def to_str(self, dot_style: bool = False, color: str = "black") -> str:
        s = f'<font color="{color}"><b>{self.get_id(cse=False)}</b></font>' \
            if dot_style else f"{self.get_id()}"
        s += f": call {self.func_name}("
        # Args
        s += ",".join([str(arg.get_id()) for arg in self.call_args])
        s += ")"
        return s

    def __str__(self) -> str:
        return self.to_str(dot_style=False)

    def is_common_subexpression(self, __o: SSAValue) -> bool:
        return False

    def is_cs_kill(self, __o) -> bool:
        return False

    def get_cs(self) -> Inst:
        return None

    def replace_operand(self, _from: Inst, _from_ident: int, _to: Inst) -> None:
        return

    def get_id(self, cse: bool = True) -> int:
        return self.id


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

