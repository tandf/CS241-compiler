from __future__ import annotations
from typing import List, Dict, Set
import SSA


class CommonSubexpressionTable:
    table: Dict[SSA.OP, SSA.Inst]

    BLACK_LIST = {SSA.OP.READ, SSA.OP.WRITE, SSA.OP.WRITENL}

    def __init__(self):
        self.table = {op: None for op in SSA.OP}

    def set(self, op: SSA.OP, inst: SSA.Inst) -> None:
        if op in CommonSubexpressionTable.BLACK_LIST:
            # Some instructions have side effects and cannot be eliminated
            return
        self.table[op] = inst

    def get(self, op: SSA.OP) -> SSA.Inst:
        assert(op in self.table)
        return self.table[op]

    def search(self, inst: SSA.Inst) -> SSA.Inst:
        head = self.table[inst.op]
        while head:
            if head.is_common_subexpression(inst):
                if head.common_subexpression:
                    head = head.common_subexpression
                break
            head = head.op_last_inst
        return head


class ValueTable:
    table: Dict[int, SSA.Inst]

    def __init__(self):
        self.table = {}  # {identifier id: SSA inst}

    def set(self, ident: int, inst: SSA.Inst) -> None:
        self.table[ident] = inst

    def get(self, ident: int) -> SSA.Inst:
        return self.table[ident]

    def update(self, __o: ValueTable) -> None:
        self.table.update(__o.table)


class Block:
    last: Block
    next: Block
    id: int

    CNT = 0

    def __init__(self):
        self.last = None
        self.next = None

        # Unique block id
        self.id = Block.CNT
        Block.CNT += 1

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Block) and __o.id == self.id

    def __hash__(self) -> int:
        return self.id

    def __str__(self) -> str:
        raise Exception("Unimplemented!")

    def __repr__(self) -> str:
        return self.__str__()

    def last_bb(self) -> BasicBlock:
        # Return last basic block.
        if isinstance(self.last, SuperBlock):
            return self.last.get_lastbb()
        else:
            return self.last

    def next_bb(self) -> BasicBlock:
        # Return next basic block.
        if isinstance(self.next, SuperBlock):
            return self.next.get_firstbb()
        else:
            return self.next

    def get_value_table(self) -> ValueTable:
        # Value table at the end of the block. Can reflect the new assignments.
        raise Exception("Unimplemented!")

    def replace_operand(self, _from: SSA.Inst, _from_ident: int,
                        _to: SSA.Inst) -> None:
        # Change all usages of _from to _to. This is for loop statements
        raise Exception("Unimplemented!")

    def dot_name(self) -> str:
        return f"Block{self.id}"

    def get_bbs(self) -> Set[BasicBlock]:
        # Return all basic blocks within this block. If this is a basic block,
        # return itself. If it's a superblock, return all basic blocks inside.
        raise Exception("Unimplemented!")


class BasicBlock(Block):
    value_table: ValueTable
    cs_table: CommonSubexpressionTable
    insts: List[SSA.Inst]
    bbid: int

    ALL_BB: List[BasicBlock]

    # Global count of all basic blocks
    CNT = 0
    ALL_BB = []

    def __init__(self):
        super().__init__()
        self.value_table = ValueTable()
        self.cs_table = CommonSubexpressionTable()
        self.insts = []

        # Unique basic block id
        self.bbid = BasicBlock.CNT
        BasicBlock.CNT += 1
        BasicBlock.ALL_BB.append(self)

    def get_value_table(self) -> ValueTable:
        return self.value_table

    def add_inst(self, inst: SSA.Inst) -> None:
        self.insts.append(inst)

    def replace_operand(self, _from: SSA.Inst, _from_ident: int,
                        _to: SSA.Inst) -> None:
        for inst in self.insts:
            inst.replace_operand(_from, _from_ident, _to)

    def get_all_insts(self) -> List[SSA.Inst]:
        return self.insts

    def get_bbs(self) -> Set[BasicBlock]:
        return set([self])

    def dot_name(self) -> str:
        return f"BB{self.bbid}"

    def dot_label(self) -> str:
        if self.insts:
            insts_str = "|".join([inst.to_str(dot_style=True)
                                 for inst in self.insts])
        else:
            insts_str = "empty"
        return f"<<b>BB{self.bbid}</b> | {{{insts_str}}}>"


class SimpleBB(BasicBlock):
    def __init__(self):
        super().__init__()

    def __str__(self) -> str:
        return f"SimpleBB{self.bbid} b{self.id}"

    def merge_before(self, __o: SimpleBB) -> SimpleBB:
        if __o:
            # TODO: combine another simple block
            pass
        return self


class BranchBB(BasicBlock):
    branchBlock: Block

    def __init__(self):
        super().__init__()
        self.branchBlock = None

    def __str__(self) -> str:
        return f"BranchBB{self.bbid} b{self.id}"

    def get_branch_head(self):
        if self.branchBlock and isinstance(self.branchBlock, SuperBlock):
            return self.branchBlock.head
        else:
            return self.branchBlock


class JoinBB(BasicBlock):
    joiningBlock: Block
    phiInsts: List[SSA.Inst]

    def __init__(self):
        super().__init__()
        self.joiningBlock = None
        self.phiInsts = []

    def __str__(self) -> str:
        return f"JoinBB{self.bbid} b{self.id}"

    def get_joining_tail(self):
        if self.joiningBlock and isinstance(self.joiningBlock, SuperBlock):
            return self.joiningBlock.tail
        else:
            return self.joiningBlock

    def get_all_insts(self) -> List[SSA.Inst]:
        return self.phiInsts + self.insts


class SuperBlock(Block):
    # A group of basic blocks with one entry and one exit

    head: Block  # First block in the super block.
    tail: Block  # Last block in the super block. Can be the same as head.
    name: str    # Describe the super block, e.g. "while statement"

    def __init__(self, name: str = ""):
        super().__init__()
        self.head = None
        self.tail = None
        self.name = name

    def __str__(self) -> str:
        return f"SuperBlock b{self.id}"

    def get_firstbb(self) -> BasicBlock:
        if isinstance(self.head, SuperBlock):
            return self.head.get_firstbb()
        return self.head

    def get_lastbb(self) -> BasicBlock:
        if isinstance(self.tail, SuperBlock):
            return self.tail.get_lastbb()
        return self.tail

    def get_value_table(self) -> ValueTable:
        # TODO: Merge value table from tail to head
        pass

    def replace_operand(self, _from: SSA.Inst, _from_ident: int,
                        _to: SSA.Inst) -> None:
        # TODO: Replace operands from head to tail
        pass

    def dot_name(self) -> str:
        return f"cluster_{self.id}"

    def dot_label(self) -> str:
        label = self.name if self.name else f"super block {self.id}"
        return f"<<I>{label}</I>>"

    def get_bbs(self) -> Set[BasicBlock]:
        ret = set()

        block = self.head
        ret.update(block.get_bbs())

        while block != self.tail:
            if isinstance(block, BranchBB):
                assert(block.branchBlock)
                ret.update(block.branchBlock.get_bbs())

            block = block.next
            if block is None:
                assert(self.tail is None)
            else:
                ret.update(block.get_bbs())

        if isinstance(block, BranchBB):
            assert(block.branchBlock)
            ret.update(block.branchBlock.get_bbs())

        return ret
