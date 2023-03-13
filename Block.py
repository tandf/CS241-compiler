from __future__ import annotations
from typing import List, Dict, Set
import copy
import SSA


class CSTable:
    table: Dict[SSA.OP, SSA.Inst]

    BLACK_LIST = SSA.OP.IO_OP | SSA.OP.BRANCH_OP | {SSA.OP.PHI}

    def __init__(self):
        self.table = {op: None for op in set(SSA.OP) - CSTable.BLACK_LIST}
        del self.table[SSA.OP.STORE]

    def add_inst(self, inst: SSA.Inst, op: SSA.OP) -> None:
        assert op in self.table, f"Adding unknown OP {op} to cs table!"
        self.table[op] = inst

    def get(self, op: SSA.OP) -> SSA.Inst:
        assert op in self.table, f"Cannot get op: {op} not in cs table!"
        return self.table[op]

    def __str__(self) -> str:
        return str(self.table)

    def __repr__(self) -> str:
        return self.__str__()


class ValueTable:
    table: Dict[int, SSA.Inst]

    def __init__(self):
        self.table = {}  # {identifier id: SSA inst}

    def has(self, ident: int) -> bool:
        if ident in self.table:
            assert self.table[ident].identifier == ident
            return True
        return False

    def set(self, ident: int, inst: SSA.Inst) -> None:
        _inst = copy.deepcopy(inst)
        _inst.identifier = ident
        self.table[ident] = _inst

    def get(self, ident: int) -> SSA.Inst:
        assert self.table[ident].identifier == ident
        return self.table[ident]

    def update(self, __o: ValueTable) -> None:
        self.table.update(__o.table)

    def get_ids(self) -> Set[int]:
        return set(self.table.keys())


class Block:
    prev: Block
    next: Block
    id: int

    CNT = 0

    def __init__(self):
        self.prev = None
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

    def set_prev(self, block: Block) -> None:
        self.prev = block

    def set_next(self, block: Block) -> None:
        self.next = block

    def _prev_bb(self) -> BasicBlock:
        # Return prev basic block.
        if self.prev is None:
            return self.prev
        if isinstance(self.prev, SuperBlock):
            return self.prev.get_lastbb()
        else:
            return self.prev

    def prev_bb(self) -> BasicBlock:
        bb = self._prev_bb()
        assert bb is not None, \
            "The BasicBlock is not well connected: no prev_bb found!"
        if bb == self:
            return None
        else:
            return bb

    def _next_bb(self) -> BasicBlock:
        # Return next basic block.
        if self.next is None:
            return self.next
        if isinstance(self.next, SuperBlock):
            return self.next.get_firstbb()
        else:
            return self.next

    def next_bb(self) -> BasicBlock:
        bb = self._next_bb()
        assert bb is not None, \
            "The BasicBlock is not well connected: no next_bb found!"
        if bb == self:
            return None
        else:
            return bb

    def get_value_table(self) -> ValueTable:
        # Value table at the end of the block. Can reflect the new assignments.
        raise Exception("Unimplemented!")

    def lookup_value_table(self, id: int) -> SSA.SSAValue:
        block = self
        while True:
            value_table = block.get_value_table()
            if value_table.has(id):
                return value_table.get(id)
            if block.prev == block:
                return None
            block = block.prev
        return None

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
    last_cs_block: BasicBlock
    cs_table: CSTable
    insts: List[SSA.Inst]
    bbid: int

    ALL_BB: List[BasicBlock]

    # Global count of all basic blocks
    CNT = 0
    ALL_BB = []

    def __init__(self):
        super().__init__()
        self.value_table = ValueTable()
        self.last_cs_block = None
        self.cs_table = CSTable()
        self.insts = []

        # Unique basic block id
        self.bbid = BasicBlock.CNT
        BasicBlock.CNT += 1
        BasicBlock.ALL_BB.append(self)

    def get_prev_cs_bb(self) -> BasicBlock:
        # If returns None, means this is the first block
        if self.last_cs_block:
            return self.last_cs_block
        else:
            return self.prev_bb()

    def get_value_table(self) -> ValueTable:
        return self.value_table

    def get_insts(self, cse: bool = True) -> List[SSA.SSAValue]:
        if cse:
            return [inst for inst in self.insts
                    if not isinstance(inst, SSA.Inst) or inst.get_cs() is None]
        else:
            return self.insts

    def get_first_inst(self, cse: bool = True) -> SSA.Inst:
        insts = self.get_insts(cse=cse)
        if insts:
            return insts[0]
        else:
            return None

    def _update_cs_table(self, inst: SSA.Inst) -> None:
        # Link the instruction in the cs table
        op = inst.op

        # Ignore some of the instructions
        if op in CSTable.BLACK_LIST:
            return

        # Store list is merged with the load list to perform kills
        if op == SSA.OP.STORE:
            op = SSA.OP.LOAD

        # TODO: kill inst for array operations

        # Find last inst from last_cs_block
        bb = self
        op_last_inst = None
        while bb is not None:
            op_last_inst = bb.cs_table.get(op)
            if op_last_inst is not None:
                break
            bb = bb.get_prev_cs_bb()

        inst.op_last_inst = op_last_inst
        self.cs_table.add_inst(inst, op)

    def add_inst(self, ssa: SSA.SSAValue) -> None:
        if isinstance(ssa, SSA.Inst):
            self._update_cs_table(ssa)
        self.insts.append(ssa)

    def add_nop(self) -> SSA.Inst:
        nop = SSA.Inst(SSA.OP.NOP)
        self.insts.append(nop)
        return nop

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

    def dot_label(self, color: str = "black", cse: bool = True) -> str:
        insts = self.get_insts(cse=cse)
        if insts:
            insts_str = "|".join([inst.to_str(dot_style=True, color=color)
                                 for inst in insts])
        else:
            insts_str = "empty"
        return f"<<b>BB{self.bbid}</b> | {{{insts_str}}}>"


class SimpleBB(BasicBlock):
    def __init__(self):
        super().__init__()

    def __str__(self) -> str:
        return f"SimpleBB{self.bbid} b{self.id}"


class BranchBB(BasicBlock):
    branchBlock: Block

    def __init__(self):
        super().__init__()
        self.branchBlock = None

    def __str__(self) -> str:
        return f"BranchBB{self.bbid} b{self.id}"

    def next_bb_branch(self) -> BasicBlock:
        if self.branchBlock:
            if isinstance(self.branchBlock, SuperBlock):
                return self.branchBlock.get_firstbb()
            else:
                return self.branchBlock
        return None


class JoinBB(BasicBlock):
    joiningBlock: Block
    phiInsts: List[SSA.Inst]

    def __init__(self):
        super().__init__()
        self.joiningBlock = None
        self.phiInsts = []

    def __str__(self) -> str:
        return f"JoinBB{self.bbid} b{self.id}"

    def last_bb_join(self) -> BasicBlock:
        if self.joiningBlock:
            if isinstance(self.joiningBlock, SuperBlock):
                return self.joiningBlock.get_lastbb()
            else:
                return self.joiningBlock
        return None

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

    def set_prev(self, block: Block) -> None:
        super().set_prev(block)
        firstbb = self.get_firstbb()
        if firstbb:
            firstbb.prev = block

    def set_next(self, block: Block) -> None:
        super().set_next(block)
        lastbb = self.get_lastbb()
        if lastbb:
            lastbb.next = block

    def get_value_table(self) -> ValueTable:
        # Merge value table from head to tail
        blocks = []
        block = self.tail
        while block != self.head:
            assert block is not None
            blocks.append(block)
            if isinstance(block, JoinBB):
                assert block.joiningBlock is not None
                blocks.append(block.joiningBlock)
            block = block.prev
        blocks.append(self.head)

        value_table = ValueTable()
        while blocks:
            block = blocks.pop()
            value_table.update(block.get_value_table())
        return value_table

    def replace_operand(self, _from: SSA.Inst, _from_ident: int,
                        _to: SSA.Inst) -> None:
        for bb in self.get_bbs():
            bb.replace_operand(_from, _from_ident, _to)

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
