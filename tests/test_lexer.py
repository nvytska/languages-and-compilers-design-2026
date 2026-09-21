import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compiler import CompileError, lex


class LexerTests(unittest.TestCase):
    def test_worked_example(self):
        tokens = lex(b"   i32 mut x{ 10 }\n    var t")
        self.assertEqual(
            [[(t.kind, t.text, t.line, t.column) for t in line] for line in tokens],
            [[("keyword", "i32", 1, 4), ("keyword", "mut", 1, 8),
              ("identifier", "x", 1, 12), ("lbrace", "{", 1, 13),
              ("number", "10", 1, 15), ("rbrace", "}", 1, 18),
              ("endline", "\\n", 1, 19)],
             [("identifier", "var", 2, 5), ("identifier", "t", 2, 9)]],
        )

    def test_adjacent_tokens_and_operators(self):
        self.assertEqual([t.text for t in lex(b"x:=10+2-3*4")[0]],
                         ["x", ":=", "10", "+", "2", "-", "3", "*", "4"])

    def test_keyword_lookup_and_unsigned_numbers(self):
        self.assertEqual([(t.kind, t.text) for t in lex(b"i32x _x2 exit -255")[0]],
                         [("identifier", "i32x"), ("identifier", "_x2"),
                          ("keyword", "exit"), ("operator", "-"), ("number", "255")])

    def test_blank_lines_and_tabs(self):
        lines = lex(b"\n\t x\n")
        self.assertEqual(len(lines), 2)
        self.assertEqual((lines[1][0].line, lines[1][0].column), (2, 3))
        self.assertEqual(lex(b" \t"), [])
        self.assertEqual(lex(b""), [])

    def test_errors(self):
        cases = [(b"\n       $", "line 2:8: unexpected byte '$'"),
                 (b"i32 x{10\n}", "line 1:6: '{' is not closed before the end of the line"),
                 (b"i32 x{10", "line 1:6: '{' is not closed before the end of the line"),
                 (b"  10x", "line 1:3: letter inside number"),
                 (b"x: 1", "line 1:2: ':' must be followed by '='"),
                 (b"x:", "line 1:2: ':' must be followed by '='"),
                 (b"=", "line 1:1: unexpected byte '='"),
                 (b"\xff", "line 1:1: unexpected byte '0xff'")]
        for source, expected in cases:
            with self.subTest(source=source):
                with self.assertRaises(CompileError) as context:
                    lex(source)
                self.assertEqual(str(context.exception), expected)


if __name__ == "__main__":
    unittest.main()
