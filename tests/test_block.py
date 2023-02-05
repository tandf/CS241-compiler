import sys
import os

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/..")

from Block import *
import SSA
import unittest


class TestBlock(unittest.TestCase):
    def setUp(self) -> None:
        SSA.Inst._init()
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


