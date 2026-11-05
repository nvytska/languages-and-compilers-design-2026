import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compiler import CompileError, Parser, SemanticAnalyzer, lex


def analyze(source):
    program = Parser(lex(source.encode("ascii"))).parse_program()
    analyzer = SemanticAnalyzer()
    analyzer.visit(program)
    return program, analyzer


def function(name="f", params="", returns="i32", body="exit 0"):
    return f"fn {name} := ({params}) -> {returns}\n{{\n{body}\n}}\n"


class FunctionSemanticTests(unittest.TestCase):
    def test_recursion_and_later_functions(self):
        program, analyzer = analyze(
            function("first", "i32 n", body="exit second(n)")
            + function("second", "i32 n", body="exit first(n)")
            + function("self", "i32 n", body="exit self(n - 1)")
            + "exit first(1)"
        )
        self.assertIs(program.functions[0].body.exit.value.function, program.functions[1])
        self.assertIs(program.functions[2].body.exit.value.function, program.functions[2])
        self.assertIsNone(analyzer.current_function)
        self.assertEqual(analyzer.scopes, [{}])

    def test_argument_widening_and_struct_return(self):
        analyze(function(params="i64 x", returns="i64", body="exit x") + "exit f(1)")
        analyze(
            "struct Point\n{\ni32 x\n}\n"
            + function(params="Point p", returns="Point", body="exit p")
            + "Point p{1}\nPoint q{f(p)}\nexit 0"
        )

    def test_invalid_functions(self):
        cases = [
            ("exit unknown(3)", "unknown function 'unknown'"),
            (function(params="i32 a, i32 b") + "exit f(1)", "expects 2 arguments, got 1"),
            (function(params="i32 a") + "exit f(true)", "expected i32, got bool"),
            (function(returns="bool", body="exit 10") + "exit 0", "must return bool, got i32"),
            (function(returns="i64", body="exit 10") + "exit 0", "must return i64, got i32"),
            (function(params="i32 x", body="x := 5\nexit x") + "exit 0", "cannot assign to a constant variable or field"),
            (function(body="exit x") + "i32 x{10}\nexit 0", "used before its declaration"),
            (function(body="i32 x{1}") + "exit 0", "must end with exit"),
            (function(params="Unknown x") + "exit 0", "unknown parameter type 'Unknown'"),
            (function(returns="Unknown") + "exit 0", "unknown return type 'Unknown'"),
            (function(params="i32 x, bool x") + "exit 0", "duplicate parameter 'x'"),
            (function() + function() + "exit 0", "already declared"),
            (function(body="i32 local{1}\nexit local") + "exit local", "used before its declaration"),
            ("struct Point\n{\ni32 x\n}\nPoint p{1}\nexit p", "top-level exit must return a built-in type"),
            (function(returns="bool", body="if true\n{\nexit 1\n}\nexit false") + "exit 0", "must return bool, got i32"),
        ]
        for source, message in cases:
            with self.subTest(source=source):
                with self.assertRaises(CompileError) as context:
                    analyze(source)
                self.assertIn(message, str(context.exception))


if __name__ == "__main__":
    unittest.main()
