from __future__ import annotations
from typing import List
import math

class VarType:
    dims: List[int]

    _SCALAR = None

    @classmethod
    def Scalar(cls) -> VarType:
        if not cls._SCALAR:
            cls._SCALAR = VarType(None)
        return cls._SCALAR

    def __init__(self, dims: List[int]) -> None:
        self.dims = dims

    def is_array(self) -> bool:
        return bool(self.dims)

    def size(self) -> int:
        if self.is_array:
            return 4 * math.prod(self.dims)
        else:
            return 4

    def __str__(self) -> str:
        if not self.is_array():
            return "var"
        else:
            s = "array"
            for dim in self.dims:
                s += f"[{dim}]"
            return s

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, __o: object) -> bool:
        assert(isinstance(__o, VarType))

        # Check if any of these two is scalar
        if self.dims is None:
            return __o.dims is None
        elif self.dims is None:
            return False

        for this, that in zip(self.dims, __o.dims):
            if this != that:
                return False
        return True


class FuncType:
    # TODO
    def __init__(self) -> None:
        pass
