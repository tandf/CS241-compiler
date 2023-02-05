import sys
import os

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/..")

from SSA import *
import unittest


class TestSSA(unittest.TestCase):
    def setUp(self) -> None:
        SSAValue._init()
        return super().setUp()

    def test_ssavalue(self):
        self.assertEqual(SSAValue.CNT, 0)
        i1 = Inst(OP.READ)
        i2 = Const.get_const(3)
        i3 = Inst(OP.ADD, x=i1, y=i2)
        i4 = Inst(OP.ADD, x=i1, y=i2, op_last_inst=i3)
        i5 = Inst(OP.ADD, x=i1, y=i2)
        i5.common_subexpression = i3
        self.assertEqual(SSAValue.CNT, 5)

        self.assertEqual(i1.id, 0)
        self.assertEqual(i2.id, 1)
        self.assertEqual(i3.id, 2)
        self.assertEqual(i4.id, 3)
        self.assertEqual(i5.id, 4)

        self.assertEqual(SSAValue.get_inst(0), i1)
        self.assertEqual(SSAValue.get_inst(1), i2)
        self.assertEqual(SSAValue.get_inst(2), i3)
        self.assertEqual(SSAValue.get_inst(3), i4)
        self.assertEqual(SSAValue.get_inst(4), i5)

        self.assertEqual(i1.common_subexpression, None)
        self.assertEqual(i5.common_subexpression, i3)

