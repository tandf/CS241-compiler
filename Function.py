from Block import SuperBlock, SimpleBB
from SSA import Const, OP, FramePointer, SSAValue
import copy
from Types import *
from IRVis import IRVis


PREDEFINED_FUNCTIONS = {
    # Name: (OP, arg_num, id)
    "InputNum": [OP.READ, 0, -1],
    "OutputNum": [OP.WRITE, 1, -1],
    "OutputNewLine": [OP.WRITENL, 0, -1]
}


class FuncContext:
    identType: Dict[int, IdentType]
    constBlock: SimpleBB
    consts: List[Const]

    def __init__(self) -> None:
        self.identType = {}
        self.constBlock = None
        self.consts = []

    def identDefined(self, id: int) -> bool:
        if id in self.identType:
            return True
        else:
            for _, v in PREDEFINED_FUNCTIONS.items():
                assert v[2] != -1
                if id == v[2]:
                    return True
            return False

    def getIdent(self, id: int) -> IdentType:
        assert isinstance(id, int)
        if id in self.identType:
            return self.identType[id]
        else:
            return None

    def setIdent(self, id: int, _type: IdentType) -> None:
        assert isinstance(id, int)
        assert isinstance(_type, IdentType)
        self.identType[id] = _type

    def getConst(self, num: int) -> Const:
        # Find constant value from created constants
        for c in self.consts:
            if c.num == num:
                return copy.copy(c)

        # Create if not found
        const = Const(num)
        self.consts.append(const)
        # Add to const block
        assert self.constBlock is not None
        self.constBlock.add_inst(const)
        return copy.copy(const)


class FuncType(IdentType):
    funcCtx: FuncContext
    func_name: str
    is_void: bool
    args: List[SSAValue]

    superBlock: SuperBlock

    def __init__(self, func_name: str, is_void: bool) -> None:
        self.func_name = func_name
        self.is_void = is_void
        self.funcCtx = FuncContext()
        self.args = []

        # Create blocks
        label = f"{self.func_name}()"
        if self.is_void:
            label = "void " + label
        self.superBlock = SuperBlock(label)
        self.constBlock = SimpleBB()
        self.endBlock = SimpleBB()
        self.bodyBlock = SuperBlock("function body")

        self.constBlock.add_inst(FramePointer())
        self.constBlock.set_prev(self.constBlock)  # To itself, meaning the first
        self.constBlock.set_next(self.bodyBlock)
        self.endBlock.set_prev(self.bodyBlock)
        self.endBlock.set_next(self.endBlock)  # To itself, meaning the last

        self.superBlock.head = self.constBlock
        self.superBlock.tail = self.endBlock

        self.funcCtx.constBlock = self.constBlock

    def __str__(self) -> str:
        s = ""
        if self.is_void:
            s += "void"
        s += f" func {self.func_name} ("

        s += ")"
        return s

    def add_arg(self, arg: SSAValue) -> None:
        self.args.append(arg)

    def vis(self, vis: IRVis) -> None:
        vis.block(self.superBlock)
