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
    insts: List[SSA.Inst]

    def __init__(self):
        self.next_block = None
        self.insts = []

    def get_value_table(self) -> ValueTable:
        # Value table at the end of the block. Can reflect the new assignments.
        raise Exception("Unimplemented!")

    def change_SSA_id(self, _from: SSA.Inst, _to: SSA.Inst) -> None:
        # Change all usages of _from to _to. This is for loop statements
        raise Exception("Unimplemented!")


class BasicBlock(Block):
    value_table: ValueTable
    cs_table: CommonSubexpressionTable

    def __init__(self):
        self.value_table = ValueTable()
        self.cs_table = CommonSubexpressionTable()

    def get_value_table(self) -> ValueTable:
        return


class BranchBB(BasicBlock):
    branchBlock: BasicBlock

    def __init__(self):
        self.branchBlock = None


class JoinBB(BasicBlock):
    joiningBlocks: List[BasicBlock]

    def __init__(self):
        self.joiningBlocks = []


class SuperBlock(Block):
    # A group of basic blocks with one entry and one exit

    head: BasicBlock
    tail: BasicBlock

    def __init__(self):
        self.head = None
        self.tail = None

    def get_value_table(self) -> ValueTable:
        pass
