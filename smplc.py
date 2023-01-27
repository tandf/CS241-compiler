#! /bin/env python3

from Tokenizer import Tokenizer, Token

class Interpreter:
    def __init__(self, file: str):
        self.file = file
        self.tokenizer = Tokenizer(self.file)
        self.inputSym = None
        # Mapping of identifiers (int) and their value (float or int)
        self.identifiers = {}

        # Read the first token
        self.next()

    def next(self) -> None:
        self.inputSym = self.tokenizer.getNext()

    def factor(self):  # Return an int or a float
        if self.inputSym.type == Token.IDENT:
            id = self.tokenizer.id
            assert id in self.identifiers, f"Uninitalized variable {self.inputSym.sym}"
            self.next()
            return self.identifiers[id]

        elif self.inputSym.type == Token.NUMBER:
            num = self.tokenizer.num
            self.next()
            return num

        elif self.inputSym.type == Token.OPENPAREN:
            self.next()
            result = self.expression()
            assert self.inputSym.type == Token.CLOSEPAREN, "Unmatched parentheses in factor!"
            self.next()
            return result

        else:
            assert False, f"Factor starts with unexpected token {self.inputSym}"

    def term(self):  # Return an int or a float
        result = self.factor()

        while True:
            if self.inputSym.type == Token.TIMES:
                self.next()
                result *= self.factor()
            elif self.inputSym.type == Token.DIV:
                self.next()
                result /= self.factor()
            else:
                return result

    def expression(self):  # Return an int or a float
        result = self.term()

        while True:
            if self.inputSym.type == Token.PLUS:
                self.next()
                result += self.term()
            elif self.inputSym.type == Token.MINUS:
                self.next()
                result -= self.term()
            else:
                return result

    def assignment(self) -> None:
        assert self.inputSym.type == Token.VAR, "Expecting keyword " \
            f"\"var\", found {self.inputSym}"
        self.next()

        assert self.inputSym.type == Token.IDENT, "Expecting variable " \
            f"name after keyword var, found {self.inputSym}"
        id = self.tokenizer.id
        self.next()

        assert self.inputSym.type == Token.BECOMES, "Expecting \"<-\" " \
            f"after variable name, found {self.inputSym}"
        self.next()

        val = self.expression()

        self.identifiers[id] = val

        assert self.inputSym.type == Token.SEMI, "Expecting \";\" " \
            f"at the end of variable assignment, found {self.inputSym}"
        self.next()

    def computation(self):  # Return an int or a float
        assert self.inputSym.type == Token.MAIN, "Expecting \"computation\" " \
            f"at the start of computation, found {self.inputSym}"
        self.next()

        while self.inputSym.type == Token.VAR:
            self.assignment()

        while True:
            result = self.expression()
            print(result)

            if self.inputSym.type != Token.SEMI:
                break
            self.next()

        assert self.inputSym.type == Token.PERIOD, "Expecting \".\" at the " \
            f"end of computation, found {self.inputSym}"
        self.next()

        return result


if __name__ == "__main__":
    interpreter = Interpreter("input.txt")
    interpreter.computation()
