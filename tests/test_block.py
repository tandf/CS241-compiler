import sys
import os

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/..")

from Block import *
import SSA
import unittest


class TestBlock(unittest.TestCase):
    def setUp(self) -> None:
        SSA.Inst._init()
        BasicBlock.CNT = 0
        BasicBlock.ALL_BB = []
        Block.CNT = 0
        return super().setUp()

    def test_commonsubexpressiontable(self):
        cs_table = CommonSubexpressionTable()

        i1 = SSA.Inst(SSA.OP.READ, op_last_inst=cs_table.get(SSA.OP.READ))
        cs = cs_table.search(i1)
        self.assertEqual(cs, None)
        i1.common_subexpression = cs
        cs_table.set(SSA.OP.ADD, i1)

        i2 = SSA.Inst(SSA.OP.READ, op_last_inst=cs_table.get(SSA.OP.READ))
        cs = cs_table.search(i2)
        self.assertEqual(cs, None)
        i2.common_subexpression = cs
        cs_table.set(SSA.OP.ADD, i2)

        i3 = SSA.Inst(SSA.OP.READ, op_last_inst=cs_table.get(SSA.OP.READ))
        cs = cs_table.search(i3)
        self.assertEqual(cs, None)
        i3.common_subexpression = cs
        cs_table.set(SSA.OP.ADD, i3)

        add1 = SSA.Inst(SSA.OP.ADD, x=i1, y=i2,
                        op_last_inst=cs_table.get(SSA.OP.ADD))
        cs = cs_table.search(add1)
        self.assertEqual(cs, None)
        add1.common_subexpression = cs
        cs_table.set(SSA.OP.ADD, add1)

        add2 = SSA.Inst(SSA.OP.ADD, x=i1, y=i3,
                        op_last_inst=cs_table.get(SSA.OP.ADD))
        cs = cs_table.search(add2)
        self.assertEqual(cs, None)
        add2.common_subexpression = cs
        cs_table.set(SSA.OP.ADD, add2)

        add3 = SSA.Inst(SSA.OP.ADD, x=i1, y=i2,
                        op_last_inst=cs_table.get(SSA.OP.ADD))
        cs = cs_table.search(add3)
        self.assertEqual(cs, add1)
        add3.common_subexpression = cs
        cs_table.set(SSA.OP.ADD, add3)

        add4 = SSA.Inst(SSA.OP.ADD, x=i2, y=i1,
                        op_last_inst=cs_table.get(SSA.OP.ADD))
        cs = cs_table.search(add3)
        self.assertEqual(cs, add1)
        add4.common_subexpression = cs
        cs_table.set(SSA.OP.ADD, add4)

    def test_valuetable(self):
        valueTable = ValueTable()
        valueTable2 = ValueTable()
        cs_table = CommonSubexpressionTable()

        i1 = SSA.Inst(SSA.OP.READ, op_last_inst=cs_table.get(SSA.OP.READ))
        i2 = SSA.Inst(SSA.OP.READ, op_last_inst=cs_table.get(SSA.OP.READ))

        valueTable.set(1, i1)
        valueTable.set(2, i2)
        self.assertEqual(valueTable.get(1), i1)
        self.assertEqual(valueTable.get(2), i2)

        i3 = SSA.Inst(SSA.OP.READ, op_last_inst=cs_table.get(SSA.OP.READ))
        valueTable2.set(1, i3)
        self.assertEqual(valueTable2.get(1), i3)

        valueTable.update(valueTable2)
        self.assertEqual(valueTable.get(1), i3)
        self.assertEqual(valueTable.get(2), i2)

    def test_bbid(self):
        b0 = SimpleBB()
        b1 = BranchBB()
        b2 = JoinBB()
        b3 = SimpleBB()

        self.assertEqual(BasicBlock.CNT, 4)

        self.assertEqual(b0.id, 0)
        self.assertEqual(b1.id, 1)
        self.assertEqual(b2.id, 2)
        self.assertEqual(b3.id, 3)

        self.assertEqual(b0, b0)
        self.assertNotEqual(b1, b0)
        self.assertNotEqual(b1, b2)
        self.assertNotEqual(b3, b2)

    def test_get_bbs_if(self):
        s1 = SuperBlock()  # A super block containing a if pattern

        ## Within s1 ##
        s1b1 = SimpleBB()
        s1branch = BranchBB()
        s1b2 = SimpleBB()
        s1b3 = SimpleBB()
        s1join = JoinBB()

        s1.head = s1b1
        s1.tail = s1join

        s1b1.next = s1branch
        s1branch.last = s1b1

        s1branch.branchBlock = s1b2
        s1branch.next = s1b3
        s1b2.last = s1branch
        s1b3.last = s1branch

        s1b2.next = s1join
        s1b3.next = s1join
        s1join.joiningBlock = s1b2
        s1join.last = s1b3

        BB = s1.get_bbs()
        self.assertEqual(len(BB), 5)
        self.assertTrue(s1b1 in BB)
        self.assertTrue(s1b2 in BB)
        self.assertTrue(s1b3 in BB)
        self.assertTrue(s1branch in BB)
        self.assertTrue(s1join in BB)

    def test_get_bbs_complex(self):
        superBlock = SuperBlock()

        b0 = SimpleBB()
        s1 = SuperBlock()  # A super block containing a if pattern
        s2 = SuperBlock()  # A super block containing two super blocks
        s3 = SuperBlock()  # A super block containing a while pattern
        b4 = SimpleBB()

        ## Connection between blocks ##
        superBlock.head = b0
        superBlock.tail = b4

        b0.next = s1
        s1.last = b0
        s1.next = s2
        s2.last = s1
        s2.next = s3
        s3.last = s2
        s3.next = b4
        b4.last = s3

        ## Within s1 ##
        s1b1 = SimpleBB()
        s1branch = BranchBB()
        s1b2 = SimpleBB()
        s1b3 = SimpleBB()
        s1join = JoinBB()

        s1.head = s1b1
        s1.tail = s1join

        s1b1.last = b0
        s1b1.next = s1branch

        s1branch.last = s1b1
        s1branch.branchBlock = s1b2
        s1branch.next = s1b3

        s1b2.last = s1branch
        s1b2.next = s1join

        s1b3.last = s1branch
        s1b3.next = s1join

        s1join.joiningBlock = s1b2
        s1join.last = s1b3
        s1join.next = s2

        ## Within s2 ##
        s2s0 = SuperBlock()
        s2s1 = SuperBlock()

        s2s0b = SimpleBB()
        s2s1b = SimpleBB()

        s2.head = s2s0
        s2.tail = s2s1

        s2s0.head = s2s0b
        s2s0.tail = s2s0b
        s2s0.last = s1
        s2s0.next = s2s1

        s2s1.head = s2s1b
        s2s1.tail = s2s1b
        s2s1.last = s2s0
        s2s1.next = s3

        s2s0b.last = s1
        s2s0b.next = s2s1

        s2s1b.last = s2s0
        s2s1b.next = s3

        ## Within s3 ##
        s3b0 = SimpleBB()
        s3join = JoinBB()
        s3branch = BranchBB()
        s3body = SuperBlock()

        s3bodyb0 = SimpleBB()
        s3bodyb1 = SimpleBB()

        s3.head = s3b0
        s3.tail = s3branch

        s3b0.last = s2
        s3b0.next = s3join

        s3join.last = s3b0
        s3join.next = s3branch
        s3join.joiningBlock = s3body

        s3branch.last = s3join
        s3branch.next = b4
        s3branch.branchBlock = s3body

        s3body.last = s3branch
        s3body.next = s3join
        s3body.head = s3bodyb0
        s3body.tail = s3bodyb1

        s3bodyb0.last = s3branch
        s3bodyb0.next = s3bodyb1
        s3bodyb1.last = s3bodyb0
        s3bodyb1.next = s3join

        ## Tests ##
        self.assertEqual(BasicBlock.CNT, 14)

        # s1
        BB1 = s1.get_bbs()
        self.assertEqual(len(BB1), 5)

        # s2
        BB2 = s2.get_bbs()
        self.assertEqual(len(BB2), 2)

        # s3
        BB3 = s3.get_bbs()
        self.assertEqual(len(BB3), 5)

        # super block
        BB = superBlock.get_bbs()
        self.assertEqual(len(BB), 14)
