from __future__ import annotations
from typing import List, Dict
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
    def __init__(self):
        pass

    def get_value_table(self) -> ValueTable:
        # Value table at the end of the block. Can reflect the new assignments.
        raise Exception("Unimplemented!")

    def replace_operand(self, _from: SSA.Inst, _from_ident: int,
                        _to: SSA.Inst) -> None:
        # Change all usages of _from to _to. This is for loop statements
        raise Exception("Unimplemented!")


class BasicBlock(Block):
    value_table: ValueTable
    cs_table: CommonSubexpressionTable
    insts: List[SSA.Inst]
    inBlock: BasicBlock
    outBlock: BasicBlock

    def __init__(self):
        self.value_table = ValueTable()
        self.cs_table = CommonSubexpressionTable()
        self.insts = []
        self.inBlock = None
        self.outBlock = None

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

class SimpleBB(BasicBlock):
    def __init__(self):
        # The simplest BasicBlock that has no joining edge or branch edge
        pass


class BranchBB(BasicBlock):
    branchBlock: BasicBlock

    def __init__(self):
        self.branchBlock = None


class JoinBB(BasicBlock):
    joiningBlock: BasicBlock
    phiInsts: List[SSA.Inst]

    def __init__(self):
        self.joiningBlock = None
        self.phiInsts = []

    def get_all_insts(self) -> List[SSA.Inst]:
        return self.phiInsts + self.insts


class SuperBlock(Block):
    # A group of basic blocks with one entry and one exit

    head: BasicBlock  # First block in the super block.
    tail: BasicBlock  # Last block in the super block. Can be the same as head.

    def __init__(self):
        self.head = None
        self.tail = None

    def get_value_table(self) -> ValueTable:
        # TODO: Merge value table from tail to head
        pass

    def replace_operand(self, _from: SSA.Inst, _from_ident: int,
                        _to: SSA.Inst) -> None:
        # TODO: Replace operands from head to tail
        pass
