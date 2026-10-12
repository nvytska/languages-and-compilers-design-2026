import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compiler import CompileError, Parser, SemanticAnalyzer, StructDeclNode, lex


POINT = "struct Point\n{\ni32 mut x\ni32 mut y\n}\n"


def analyze(source):
    analyzer = SemanticAnalyzer()
    analyzer.visit(Parser(lex(source.encode("ascii"))).parse_program())
    return analyzer


class StructSemanticTests(unittest.TestCase):
    def test_nested_initializer_types_and_widening(self):
        analyzer = analyze(
            "struct Point\n{\ni64 x\ni32 y\n}\n"
            "struct Box\n{\nPoint point\n}\n"
            "struct Outer\n{\nBox box\n}\n"
            "Outer o{{{10, 20}}}\nexit 0"
        )
        box = analyzer.scopes[0]["o"].inits[0]
        self.assertEqual(box.type_name, "Box")
        self.assertEqual(box.values[0].type_name, "Point")

    def test_nested_initializer_errors(self):
        prefix = POINT + "struct Box\n{\nPoint point\n}\n"
        for source, message in [
            (prefix + "Box b{{1}}\nexit 0", "expected 2 initializer values, got 1"),
            (prefix + "Box b{{true, 2}}\nexit 0", "cannot initialize i32 with bool"),
            (POINT + "Point p{{1}, 2}\nexit 0", "cannot use nested initializer for i32"),
            ("i32 x{{1}}\nexit 0", "cannot use nested initializer for i32"),
        ]:
            with self.subTest(source=source):
                with self.assertRaisesRegex(CompileError, message):
                    analyze(source)

    def test_copy_and_nested_structs(self):
        analyzer = analyze(
            POINT + "struct Shape\n{\nPoint origin\ni64 size\nbool visible\n}\n"
            "Point p{10, 20}\nPoint q{p}\nShape s{q, 1, true}\n"
            "Shape t{s}\nexit 0\n"
        )
        self.assertEqual(list(analyzer.structs), ["Point", "Shape"])
        self.assertEqual(analyzer.scopes[0]["t"].type_name, "Shape")

    def test_single_field_initialization(self):
        analyze("struct Box\n{\ni64 value\n}\nBox b{1}\nBox c{b}\nexit 0")

    def test_invalid_structs(self):
        cases = [
            (POINT + "Point p{10}\nexit 0", "expected 2 initializer values, got 1"),
            (POINT + "Point p{true, 20}\nexit 0", "cannot initialize i32 with bool"),
            ("struct Point\n{\nUnknown x\n}\nexit 0", "unknown field type 'Unknown'"),
            (POINT + POINT + "exit 0", "duplicate or reserved struct name 'Point'"),
            ("struct Point\n{\ni32 x\nbool x\n}\nexit 0", "duplicate field 'x'"),
            ("struct Circle\n{\nPoint center\n}\n" + POINT + "exit 0", "unknown field type 'Point'"),
            ("struct Point\n{\nPoint self\n}\nexit 0", "unknown field type 'Point'"),
            ("Unknown p{1}\nexit 0", "unknown struct type 'Unknown'"),
            ("i32 x{1, 2}\nexit 0", "primitive type requires exactly one initializer"),
            ("i32 x{true}\nexit 0", "cannot initialise 'x'"),
            ("struct Box\n{\ni32 value\n}\nBox b{2147483648}\nexit 0", "cannot initialize i32 with i64"),
            (POINT + "Point p{10, 20}\nPoint p{p}\nexit 0", "already declared in this block"),
        ]
        for source, message in cases:
            with self.subTest(source=source):
                with self.assertRaisesRegex(CompileError, message):
                    analyze(source)

    def test_reserved_struct_name(self):
        with self.assertRaisesRegex(CompileError, "reserved struct name 'i32'"):
            SemanticAnalyzer().visit(StructDeclNode(1, 1, "i32", []))


if __name__ == "__main__":
    unittest.main()
