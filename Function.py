from Block import *
from SSA import OP

class Function:
    superBlock: SuperBlock

    PREDEFINED_FUNCTIONS = {"InputNum": (OP.READ, 0),
                            "OutputNum": (OP.WRITE, 1),
                            "OutputNewLine": (OP.WRITENL, 0)}

    def __init__(self) -> None:
        self.superBlock = None
