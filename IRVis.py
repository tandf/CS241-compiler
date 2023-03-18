from graphviz import Digraph
from Block import *
import SSA

class IRVis:
    g: Digraph
    debug: bool
    # TODO: block domination

    branch_edge_color = "#D2691E"
    falltrhough_edge_color = "#00BFFF"
    superblock_color = "#40E0D0"
    instid_color = "#FF69B4"

    def __init__(self, filename: str = "graph/out.dot",
                 debug: bool = False) -> None:
        self._graph = Digraph('structs', filename=filename,
                                       node_attr={'shape': 'record'})
        self.debug = debug

    def _edge(self, src: BasicBlock, dst: BasicBlock) -> None:
        self._graph.edge(src.dot_name() + ":s", dst.dot_name() + ":n")

    def _edge_branch(self, src: BasicBlock, dst: BasicBlock) -> None:
        self._graph.edge(src.dot_name() + ":s", dst.dot_name() + ":n",
                         #  label="branch",
                         color=IRVis.branch_edge_color,
                         fontcolor=IRVis.branch_edge_color)

    def _edge_fallthrough(self, src: BasicBlock, dst: BasicBlock) -> None:
        self._graph.edge(src.dot_name() + ":s", dst.dot_name() + ":n",
                         #  label="fall through",
                         color=IRVis.falltrhough_edge_color,
                         fontcolor=IRVis.falltrhough_edge_color)

    def _superBlock(self, sb: SuperBlock, g: Digraph) -> Set[BasicBlock]:
        # Draw clusters for super blocks

        with g.subgraph(name=sb.dot_name()) as c:
            c.attr(color=IRVis.superblock_color, style="dashed",
                   label=sb.dot_label(), fontcolor=IRVis.superblock_color)

            visited = set()
            block = sb.head
            if block and isinstance(block, SuperBlock):
                visited.update(self._superBlock(block, c))

            while block and block != sb.tail:
                if isinstance(block, BranchBB) and block.branchBlock:
                    if isinstance(block.branchBlock, SuperBlock):
                        visited.update(self._superBlock(block.branchBlock, c))

                block = block.next
                if block and isinstance(block, SuperBlock):
                    visited.update(self._superBlock(block, c))

            if isinstance(block, BranchBB) and block.branchBlock:
                if isinstance(block.branchBlock, SuperBlock):
                    visited.update(self._superBlock(block.branchBlock, c))

            for b in sb.get_bbs() - visited:
                self._basicBlock(b, c)

            return sb.get_bbs()

    def _basicBlock(self, b: BasicBlock, g: Digraph) -> None:
        g.node(b.dot_name(), b.dot_label(
            IRVis.instid_color, cse=not self.debug))

    def _basicBlockEdges(self, b: BasicBlock) -> None:
        next = b.next_bb()
        # Check if this is the end block
        if next is None:
            return

        assert isinstance(next, BasicBlock)

        if isinstance(b, BranchBB):
            if next:
                self._edge_branch(b, next)
            branchBB = b.next_bb_branch()
            if branchBB:
                self._edge_fallthrough(b, branchBB)

        # Normal blocks
        elif next is not None:
                self._edge(b, next)

    def block(self, block: Block) -> None:
        if isinstance(block, SuperBlock):
            for bb in block.get_bbs():
                self._basicBlockEdges(bb)
            self._superBlock(block, self._graph)
        elif isinstance(block, BasicBlock):
            self._basicBlock(block, self._graph)
        else:
            raise("Cannot draw block that is neither a super block nor a basic "
                  f"block {block}")

    def render(self):
        self._graph.render()


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
    s1.prev = b0
    s1.next = s2
    s2.prev = s1
    s2.next = s3
    s3.prev = s2
    s3.next = b4
    b4.prev = s3

    ## Within s1 ##
    s1b1 = SimpleBB()
    s1branch = BranchBB()
    s1b2 = SimpleBB()
    s1b3 = SimpleBB()
    s1join = JoinBB()

    s1.head = s1b1
    s1.tail = s1join

    s1b1.prev = b0
    s1b1.next = s1branch

    s1branch.prev = s1b1
    s1branch.branchBlock = s1b2
    s1branch.next = s1b3

    s1b2.prev = s1branch
    s1b2.next = s1join

    s1b3.prev = s1branch
    s1b3.next = s1join

    s1join.joiningBlock = s1b2
    s1join.prev = s1b3
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
    s2s0.prev = s1
    s2s0.next = s2s1

    s2s1.head = s2s1b
    s2s1.tail = s2s1b
    s2s1.prev = s2s0
    s2s1.next = s3

    s2s0b.prev = s1
    s2s0b.next = s2s1

    s2s1b.prev = s2s0
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

    s3b0.prev = s2
    s3b0.next = s3join

    s3join.prev = s3b0
    s3join.next = s3branch
    s3join.joiningBlock = s3body

    s3branch.prev = s3join
    s3branch.next = b4
    s3branch.branchBlock = s3body

    s3body.prev = s3branch
    s3body.next = s3join
    s3body.head = s3bodyb0
    s3body.tail = s3bodyb1

    s3bodyb0.prev = s3branch
    s3bodyb0.next = s3bodyb1
    s3bodyb1.prev = s3bodyb0
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
    vis.block(superBlock)
    vis.render()
