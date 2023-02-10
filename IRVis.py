import graphviz
from Block import *
import SSA

class IRVis:
    g: graphviz.Digraph

    # TODO: Draw subgraphs for super blocks

    def __init__(self) -> None:
        self.g = graphviz.Digraph('structs', filename='graph/out.dot',
                                  node_attr={'shape': 'record'})

    def bb(self, b: BasicBlock):
        self.g.node(b.dot_name(), b.dot_label())

        if isinstance(b, BranchBB):
            branchHead = b.get_branch_head()
            if branchHead:
                self.g.edge(b.dot_name() + ":s",
                            branchHead.dot_name() + ":n", label="branch")

        next = b.next_bb()
        if next:
            self.g.edge(b.dot_name() + ":s", next.dot_name() + ":n")

    def render(self):
        self.g.render()


if __name__ == "__main__":

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

    b0.add_inst(SSA.Const(3))
    b0.add_inst(SSA.Const(12))
    b0.add_inst(SSA.Const(2))

    read1 = SSA.Inst(SSA.OP.READ)
    s1b1.add_inst(read1)

    read2 = SSA.Inst(SSA.OP.READ)
    add1 = SSA.Inst(SSA.OP.ADD, read1, read2)
    s1branch.add_inst(read2)
    s1branch.add_inst(add1)

    for bb in BasicBlock.ALL_BB:
        bb.add_inst(SSA.Inst(SSA.OP.EMPTY))

    vis = IRVis()
    bbs = superBlock.get_bbs()
    for bb in bbs:
        vis.bb(bb)
    vis.render()

