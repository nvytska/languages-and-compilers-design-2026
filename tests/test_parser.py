import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compiler import CompileError, Parser, lex


def parse(source):
    return Parser(lex(source)).parse_program()


class FunctionParserTests(unittest.TestCase):
    def test_zero_parameters_and_nested_calls(self):
        program = parse(
            b"fn zero := () -> i32\n{\nexit 0\n}\n"
            b"fn add := (i32 a, i32 b) -> i32\n{\ni32 result{a + b}\nexit result\n}\n"
            b"exit add(zero(), add(2, 3))\n"
        )
        self.assertEqual(program.functions[0].params, [])
        self.assertEqual([p.name for p in program.functions[1].params], ["a", "b"])
        self.assertEqual(program.exit.value.args[0].args, [])
        self.assertEqual(program.exit.value.args[1].name, "add")

    def test_invalid_function_syntax_and_order(self):
        function = b"fn f := () -> i32\n{\nexit 0\n}\n"
        cases = [
            (b"fn f := (i32 a,) -> i32\n", "expected parameter type"),
            (b"fn f := () i32\n", "expected '->' after parameters"),
            (b"fn f := () -> i32 {\n", "unexpected token after return type"),
            (b"i32 x{0}\n" + function + b"exit 0", "function must be declared before statements"),
            (function + b"struct P\n", "struct must be declared before functions and statements"),
            (b"exit f(1\n", "expected '\\)' after arguments"),
        ]
        for source, message in cases:
            with self.subTest(source=source):
                with self.assertRaisesRegex(CompileError, message):
                    parse(source)


class StructParserTests(unittest.TestCase):
    def test_struct_initializers_and_assignment(self):
        program = parse(
            b"struct Point\n{\n\n i32 mut x\n i32 y\n}\n"
            b"Point mut p{10 + 1, 20}\nPoint q{p}\n"
            b"i32 mut n{1}\nn := 2\nexit n\n"
        )
        self.assertEqual(program.structs[0].name, "Point")
        self.assertEqual(
            [(f.name, f.type_name, f.mutable) for f in program.structs[0].fields],
            [("x", "i32", True), ("y", "i32", False)],
        )
        self.assertEqual(len(program.statements[0].inits), 2)
        self.assertTrue(program.statements[0].mutable)
        self.assertEqual(program.statements[1].inits[0].name, "p")
        self.assertEqual(program.statements[3].label(), "Assign")
        self.assertEqual(program.statements[3].target.name, "n")

    def test_invalid_struct_syntax(self):
        cases = [
            (b"struct\n", "expected struct name"),
            (b"struct P\n", "expected '{' after struct"),
            (b"struct P\n{\ni32 x\n", "struct is never closed"),
            (b"struct P\n{\n}\nexit 0", "struct must contain at least one field"),
            (b"i32 x{1}\nstruct P\n", "struct must be declared before functions and statements"),
            (b"struct P\n{\ni32 x{1}\n}\nexit 0", "unexpected token after field declaration"),
            (b"P p{1,}\nexit 0", "expected a constant or variable"),
        ]
        for source, message in cases:
            with self.subTest(source=source):
                with self.assertRaisesRegex(CompileError, message):
                    parse(source)


if __name__ == "__main__":
    unittest.main()
