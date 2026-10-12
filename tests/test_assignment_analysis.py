import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compiler import CompileError, Parser, SemanticAnalyzer, lex


def analyze(source):
    SemanticAnalyzer().visit(Parser(lex(source.encode("ascii"))).parse_program())


def structs(x_mut="mut ", center_mut="mut "):
    return (
        f"struct Point\n{{\ni32 {x_mut}x\ni64 mut y\n}}\n"
        f"struct Circle\n{{\nPoint {center_mut}center\ni32 mut radius\n}}\n"
    )


class AssignmentSemanticTests(unittest.TestCase):
    def test_nested_write_checks_every_link(self):
        for object_mut, center_mut, x_mut in [
            ("mut ", "mut ", "mut "),
            ("", "mut ", "mut "),
            ("mut ", "", "mut "),
            ("mut ", "mut ", ""),
        ]:
            source = (
                structs(x_mut, center_mut) + "Point p{10, 20}\n"
                f"Circle {object_mut}c{{p, 5}}\nc.center.x := 25\nexit 0"
            )
            with self.subTest(object_mut=object_mut, center_mut=center_mut, x_mut=x_mut):
                if object_mut and center_mut and x_mut:
                    analyze(source)
                else:
                    with self.assertRaisesRegex(CompileError, "constant variable or field"):
                        analyze(source)

    def test_whole_struct_replacement_checks_nested_fields(self):
        tail = "Point p{10, 20}\nCircle mut c{p, 5}\nCircle d{p, 6}\nc := d\nexit 0"
        analyze(structs() + tail)
        for source in (structs(x_mut="") + tail, structs(center_mut="") + tail):
            with self.subTest(source=source):
                with self.assertRaisesRegex(CompileError, "not all fields are mutable"):
                    analyze(source)

    def test_assignment_type_rules(self):
        analyze(structs() + "Point mut p{10, 20}\np.y := 1\nexit 0")
        with self.assertRaisesRegex(CompileError, "cannot assign bool to i32"):
            analyze(structs() + "Point mut p{10, 20}\np.x := true\nexit 0")
        with self.assertRaisesRegex(CompileError, "cannot assign i64 to i32"):
            analyze("i32 mut x{1}\nx := 2147483648\nexit 0")


if __name__ == "__main__":
    unittest.main()
