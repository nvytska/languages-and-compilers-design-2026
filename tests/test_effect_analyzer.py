import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compiler import EffectAnalyzer, Parser, SemanticAnalyzer, lex


def checked(source):
    program = Parser(lex(source.encode("ascii"))).parse_program()
    SemanticAnalyzer().visit(program)
    return program


class EffectAnalyzerTests(unittest.TestCase):
    def test_effects_propagate_through_multiple_calls_and_arguments(self):
        program = checked(
            "fn wrapper := () -> i32\n{\nexit square(relay())\n}\n"
            "fn relay := () -> i32\n{\nexit loud()\n}\n"
            "fn loud := () -> i32\n{\nprint(5)\nexit 5\n}\n"
            "fn square := (i32 a) -> i32\n{\ni32 r{a * a}\nexit r\n}\nexit 0"
        )
        wrapper, relay, loud, square = program.functions
        analyzer = EffectAnalyzer()
        self.assertEqual(analyzer.collect_calls(wrapper.body), {id(square), id(relay)})
        self.assertEqual(analyzer.analyze(program), {id(wrapper), id(relay), id(loud)})

    def test_recursive_cycles_and_their_callers(self):
        program = checked(
            "fn a := () -> i32\n{\nexit b()\n}\n"
            "fn b := () -> i32\n{\nexit c()\n}\n"
            "fn c := () -> i32\n{\nexit a()\n}\n"
            "fn self := () -> i32\n{\nexit self()\n}\n"
            "fn relay := () -> i32\n{\nexit a()\n}\n"
            "fn pure := () -> i32\n{\nexit 0\n}\nexit 0"
        )
        analyzer = EffectAnalyzer()
        graph = {id(fn): analyzer.collect_calls(fn.body) for fn in program.functions}
        self.assertEqual(analyzer.recursive_functions(graph), {id(fn) for fn in program.functions[:4]})
        self.assertEqual(analyzer.analyze(program), {id(fn) for fn in program.functions[:5]})

    def test_mutation_and_callable_lambda_targets(self):
        program = checked(
            "struct Counter\n{\ni32 mut n\n"
            "fn bump := () -> i32\n{\nn := n + 1\nexit n\n}\n"
            "fn relay := () -> i32\n{\nexit bump()\n}\n"
            "fn peek := () -> i32\n{\nexit n\n}\n}\n"
            "fn loud := () -> i32\n{\nprint(5)\nexit 5\n}\n"
            "fn effectful := () -> i32\n{\n"
            "fn closure := []() -> i32\n{\nexit loud()\n}\nexit closure()\n}\n"
            "fn pure := () -> i32\n{\n"
            "fn quiet := []() -> i32\n{\nexit 5\n}\nexit quiet()\n}\nexit 0"
        )
        counter, closure, quiet = program.structs
        bump, relay, peek = counter.member_functions
        loud, effectful, pure = program.functions
        analyzer = EffectAnalyzer()
        self.assertEqual(analyzer.collect_calls(effectful.body), {id(closure.member_functions[0])})
        self.assertEqual(analyzer.collect_calls(pure.body), {id(quiet.member_functions[0])})
        self.assertEqual(analyzer.analyze(program), {
            id(bump), id(relay), id(loud), id(effectful), id(closure.member_functions[0]),
        })

    def test_read_and_while_and_reset_between_programs(self):
        program = checked(
            "fn input := () -> i32\n{\nexit read()\n}\n"
            "fn looping := () -> i32\n{\nwhile false\n{\ni32 unused{0}\n}\nexit 0\n}\nexit 0"
        )
        analyzer = EffectAnalyzer()
        effects = analyzer.analyze(program)
        self.assertEqual(effects, {id(fn) for fn in program.functions})
        self.assertEqual(analyzer.analyze(checked("exit 0")), set())


if __name__ == "__main__":
    unittest.main()
