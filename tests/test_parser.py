import sys
import os

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/..")

import unittest
from SmplCompiler import *
import tempfile


class TestDebug(unittest.TestCase):
    def check_NT(self, nt: SmplCDebug.NT, name:str):
        self.assertTrue(isinstance(nt, SmplCDebug.NT))
        self.assertEqual(nt.name, name)

    def check_token(self, token:Token, _type:int):
        self.assertTrue(isinstance(token, Token))
        self.assertEqual(token.type, _type)

    def test_varDecl(self):
        code = """
main
var a, i, j;
array[3][4] b;
{
    let a <- call InputNum();
    let i <- a;
    let j <- a;
    let b[0][0] <- call InputNum();
    let a <- a + b[0][0] + i + j;
    call OutputNum(a);
}.
"""

        with tempfile.NamedTemporaryFile() as codeTmp:
            debug = SmplCDebug()
            with open(codeTmp.name, "w") as f:
                f.write(code)
            smplCompiler = SmplCompiler(codeTmp.name, debug=debug)
            smplCompiler.computation()

            self.check_NT(debug.root[0], "computation")

            computation = debug.root[0].components
            self.check_NT(computation[1], "varDecl")
            var = computation[1].components
            self.check_NT(computation[2], "varDecl")
            array = computation[2].components
            self.check_NT(computation[4], "statSequence")

            self.check_NT(var[0], "typeDecl")
            self.check_token(var[1], Token.IDENT)
            self.check_token(var[2], Token.COMMA)
            self.check_token(var[3], Token.IDENT)
            self.check_token(var[4], Token.COMMA)
            self.check_token(var[5], Token.IDENT)

            self.check_NT(array[0], "typeDecl")
            arrayType = array[0].components
            self.check_token(array[1], Token.IDENT)

            self.check_token(arrayType[0], Token.ARR)
            self.check_token(arrayType[1], Token.OPENBRACKET)
            self.check_token(arrayType[2], Token.NUMBER)
            self.check_token(arrayType[3], Token.CLOSEBRACKET)
            self.check_token(arrayType[4], Token.OPENBRACKET)
            self.check_token(arrayType[5], Token.NUMBER)
            self.check_token(arrayType[6], Token.CLOSEBRACKET)

            statSequence = computation[4].components
            self.assertEqual(len(statSequence), 12)
            self.check_NT(statSequence[0].components[0], "assignment")
            self.check_NT(statSequence[10].components[0], "funcCall")

    def test_statements(self):
        # Test assignment, funcCall, ifStatement, whileStatement.
        # returnStatement is tested with funcDecl

        code = """
main
var a;
var b;
{
    let a <- call InputNum();
    let b <- call InputNum();
    if a <= b then
        let a <- a + 1
    fi;
    while a < b do
        call OutputNum(b);
        let b <- b / 2
    od;
    call OutputNum(a);
}.
"""

        with tempfile.NamedTemporaryFile() as codeTmp:
            debug = SmplCDebug()
            with open(codeTmp.name, "w") as f:
                f.write(code)
            smplCompiler = SmplCompiler(codeTmp.name, debug=debug)
            smplCompiler.computation()

            self.check_NT(debug.root[0], "computation")
            computation = debug.root[0].components
            self.check_NT(computation[4], "statSequence")
            statSequence = computation[4].components

            self.check_NT(statSequence[0].components[0], "assignment")
            self.check_NT(statSequence[2].components[0], "assignment")

            self.check_NT(statSequence[4].components[0], "ifStatement")
            self.check_NT(statSequence[6].components[0], "whileStatement")
            self.check_NT(statSequence[8].components[0], "funcCall")

    def test_array(self):
        code = """
main
var a, i, j;
array[3][4] b;
{
    let a <- call InputNum();
    while i < 3 do
        while j < 4 do
            let b[i][j] <- a;
            let j <- j + 1;
        od;
        let i <- i + 1;
    od;
}.
"""

        with tempfile.NamedTemporaryFile() as codeTmp:
            debug = SmplCDebug()
            with open(codeTmp.name, "w") as f:
                f.write(code)
            smplCompiler = SmplCompiler(codeTmp.name, debug=debug)
            smplCompiler.computation()

            self.check_NT(debug.root[0], "computation")
            computation = debug.root[0].components
            self.check_NT(computation[1], "varDecl")
            self.check_NT(computation[2], "varDecl")

            self.check_NT(computation[4], "statSequence")
            statSequence = computation[4].components

            self.check_NT(statSequence[0].components[0], "assignment")
            self.check_NT(statSequence[2].components[0], "whileStatement")
            outerWhile = statSequence[2].components[0].components

            self.check_NT(outerWhile[1], "relation")
            self.check_NT(outerWhile[3], "statSequence")
            outerWhileBody = outerWhile[3].components

            self.check_NT(outerWhileBody[0].components[0], "whileStatement")
            innerWhile = outerWhileBody[0].components[0].components
            self.check_NT(outerWhileBody[2].components[0], "assignment")

            self.check_NT(innerWhile[1], "relation")
            self.check_NT(innerWhile[3], "statSequence")
            innerwhileBody = innerWhile[3].components

            self.check_NT(innerwhileBody[0].components[0], "assignment")
            self.check_NT(innerwhileBody[2].components[0], "assignment")

    def test_func(self):
        code = """
main
var a;

void function myOutput(in);
{
    call OutputNum(in);
};
function myInput();
var in;
{
    let in <- call IntputNum();
    return in;
};

{
    let a <- call myInput;
    call myOutput(a);
}.
"""

        with tempfile.NamedTemporaryFile() as codeTmp:
            debug = SmplCDebug()
            with open(codeTmp.name, "w") as f:
                f.write(code)
            smplCompiler = SmplCompiler(codeTmp.name, debug=debug)
            smplCompiler.computation()

            self.check_NT(debug.root[0], "computation")
            computation = debug.root[0].components
            self.check_NT(computation[1], "varDecl")
            self.check_NT(computation[2], "funcDecl")
            self.check_NT(computation[3], "funcDecl")
