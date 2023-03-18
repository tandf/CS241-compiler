from __future__ import annotations
from typing import List, Dict
import math


class IdentType:
    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return self.__str__()


class VarType(IdentType):
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

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, VarType):
            return False

        # Check if any of these two is scalar
        if self.dims is None:
            return __o.dims is None
        elif self.dims is None:
            return False

        for this, that in zip(self.dims, __o.dims):
            if this != that:
                return False
        return True
