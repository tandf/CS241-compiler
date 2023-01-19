#! /bin/env python3

class Tokenizer:
    def __init__(self, input: str):
        self.input = input
        self.idx = 0

    def print(self) -> None:
        print(self.input[self.idx:])

    def end(self) -> bool:
        return self.idx == len(self.input)

    def sym(self) -> str:
        assert not self.end()
        return self.input[self.idx]

    def next(self) -> None:
        self.idx += 1

    def is_white_space(self) -> bool:
        return self.sym() in [" "]

    def is_digit(self) -> bool:
        assert len(self.sym()) == 1
        return ord(self.sym()) >= ord("0") and ord(self.sym()) <= ord("9")

class Project1:
    def __init__(self, tokenizer: Tokenizer):
        self.tokenizer = tokenizer

    def sym(self) -> str:
        return self.tokenizer.sym()

    def is_white_space(self) -> bool:
        return self.tokenizer.is_white_space()

    def next(self) -> None:
        self.tokenizer.next()

    def clear_white_space(self) -> None:
        while self.is_white_space():
            self.tokenizer.next()

    def is_digit(self) -> bool:
        return self.tokenizer.is_digit()

    def number(self) -> int:
        result = 0
        while self.is_digit():
            result = result * 10 + int(self.sym())
            self.next()
        self.clear_white_space()
        return result

    def factor(self) -> int:
        if self.is_digit():
            return self.number()
        elif self.sym() == "(":
            self.next()
            self.clear_white_space()
            result = self.expression()
            assert self.sym() == ")", "unmatched parentheses in factor!"
            self.next()
            self.clear_white_space()
            return result
        else:
            assert False, f"factor starts with unexpected symbol \"{self.sym()}\""

    def term(self) -> int:
        result = self.factor()

        while True:
            if self.sym() == "*":
                self.next()
                self.clear_white_space()
                result *= self.factor()
            elif self.sym() == "/":
                self.next()
                self.clear_white_space()
                result /= self.factor()
            else:
                return result

    def expression(self) -> int:
        result = self.term()

        while True:
            if self.sym() == "+":
                self.next()
                self.clear_white_space()
                result += self.term()
            elif self.sym() == "-":
                self.next()
                self.clear_white_space()
                result -= self.term()
            else:
                return result

    def computation(self) -> int:
        self.clear_white_space()
        result = self.expression()
        while self.is_white_space():
            self.next()
        assert self.sym() == ".", "computation doesn't end with \".\"!"
        self.next()
        return result


if __name__ == "__main__":

    with open("project1_input.txt", "r") as f:
        code = f.read()
        print(f"reading input: {code}")

    with open("project1_answers.txt", "r") as f:
        answers = f.read().split()
    ans_idx = 0

    t = Tokenizer(code)
    p = Project1(t)
    print(f"results:")
    while not t.end():
        result = p.computation()
        print(f"\t{result} ", end="")
        if ans_idx < len(answers) and result == int(answers[ans_idx]):
            print("[correct]")
        else:
            print("[wrong]")
        ans_idx += 1