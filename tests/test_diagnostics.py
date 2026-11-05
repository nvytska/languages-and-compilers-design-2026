import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compiler import CompileError, Parser, SemanticAnalyzer, lex


class DiagnosticTests(unittest.TestCase):
    def test_sheet_diagnostics(self):
        cases = [
            ("if true\n{\n}\nexit 0", "line 2:1: empty block"),
            ("if true\n{\n    i32 y{2}\nexit y", "line 2:1: '{' is never closed"),
            ("i32 x{5", "line 1:8: expected '}', found end of line"),
            ("i32 x{10", "line 1:9: expected '}', found end of line"),
            ("else\n{\nexit 0\n}\nexit 0", "line 1:1: 'else' without an 'if'"),
            ("i32 x{3000000000}\nexit x", "line 1:7: constant 3000000000 does not fit in i32"),
            ("i32 mut c{0}\nc := 3000000000\nexit c", "line 2:6: constant 3000000000 does not fit in i32"),
            ("i32 mut x{0}\nx := x +   \nexit x", "line 2:9: expected a constant or variable"),
            ("i32 mut x{0}\nx := x +   ", "line 2:9: expected a constant or variable"),
            ("if true\n{\nexit 0\n}\nelse\n{\n}\nexit 0", "line 6:1: empty block"),
            ("if true\n{\nexit 0\n}\nelse\n{\nexit 0", "line 6:1: '{' is never closed"),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                with self.assertRaises(CompileError) as context:
                    program = Parser(lex(source.encode("ascii"))).parse_program()
                    SemanticAnalyzer().visit(program)
                self.assertEqual(str(context.exception), expected)
