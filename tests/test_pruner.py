import gc
import sys
import unittest
import weakref
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compiler import CodeGen, DeclNode, Parser, Pruner, SemanticAnalyzer, UseCounter, lex, remove_unused
from llvmlite import binding as llvm


def checked(source):
    program = Parser(lex(source.encode("ascii"))).parse_program()
    SemanticAnalyzer().visit(program)
    return program


def optimized(source):
    program = remove_unused(checked(source))
    llvm.parse_assembly(str(CodeGen().visit(program))).verify()
    return program


class PrunerTests(unittest.TestCase):
    def test_removed_declaration_is_collected(self):
        program = checked("i32 x{10}\nexit 0")
        reference = weakref.ref(program.statements[0])
        remove_unused(program)
        gc.collect()
        self.assertIsNone(reference())

    def test_chain_rounds(self):
        program = checked("i32 x{10}\ni32 y{x}\ni32 z{15}\nexit z")
        for expected in (["x", "z"], ["z"]):
            counter = UseCounter()
            counter.visit(program)
            Pruner({key for key, reads in counter.reads.items() if reads == 0}).prune(program)
            self.assertEqual([d.name for d in program.statements], expected)
        self.assertIs(remove_unused(program), program)
        self.assertEqual([d.name for d in program.statements], ["z"])

    def test_shadowing(self):
        program = optimized(
            "i32 mut r{0}\ni32 x{1}\nif true\n{\ni32 x{10}\nr := x\n}\nexit r"
        )
        self.assertEqual([d.name for d in program.statements if isinstance(d, DeclNode)], ["r"])
        block = program.statements[1].then_block
        self.assertIs(block.statements[1].value.decl, block.statements[0])

    def test_assignment_removal_exposes_another_dead_variable(self):
        program = optimized("i32 x{5}\ni32 mut y{0}\ny := x\nexit 0")
        self.assertEqual(program.statements, [])

    def test_calls_and_input_stay(self):
        program = optimized(
            "fn loud := () -> i32\n{\nprint(7)\nexit 1\n}\n"
            "i32 x{10}\ni32 y{read()}\ni32 z{x + 5}\ni32 call{loud()}\n"
            "i32 mut assigned{0}\nassigned := loud()\nexit 0"
        )
        self.assertEqual([d.name for d in program.statements if isinstance(d, DeclNode)],
                         ["y", "call", "assigned"])
        self.assertEqual(len(program.statements), 4)

    def test_pure_call_with_input_argument_stays_but_pure_assignment_goes(self):
        program = optimized(
            "fn identity := (i32 a) -> i32\n{\nexit a\n}\n"
            "i32 input{identity(read())}\n"
            "i32 mut unused{0}\nunused := identity(5)\nexit 0"
        )
        self.assertEqual([d.name for d in program.statements], ["input"])
        self.assertEqual([fn.name for fn in program.functions], ["identity"])

    def test_nested_blocks_become_empty(self):
        program = optimized(
            "if true\n{\ni32 mut x{0}\nx := 1\n}\nelse\n{\ni32 y{2}\n}\n"
            "while false\n{\ni32 z{3}\n}\nexit 0"
        )
        self.assertEqual(program.statements[0].then_block.statements, [])
        self.assertEqual(program.statements[0].else_block.statements, [])
        self.assertEqual(program.statements[1].body.statements, [])

    def test_methods_parameters_and_fields_stay(self):
        program = optimized(
            "struct Box\n{\ni32 mut x\nfn set := (i32 v) -> i32\n{\n"
            "i32 unused{9}\nx := v\nexit 0\n}\n}\n"
            "fn make := () -> Box\n{\nBox b{1}\nexit b\n}\n"
            "Box mut dead{0}\ndead.x := 5\n"
            "Box mut protected{0}\nprotected.x := read()\n"
            "exit 0"
        )
        self.assertEqual(len(program.statements), 2)
        method = program.structs[0].member_functions[0]
        self.assertEqual(len(method.params), 1)
        self.assertEqual(len(method.body.statements), 1)
        self.assertEqual(method.body.statements[0].target.decl.name, "x")
        self.assertEqual(len(program.structs[0].fields), 1)
        self.assertEqual(len(program.functions), 0)

    def test_unused_lambda_stays_but_dead_locals_inside_it_go(self):
        program = optimized(
            "i32 k{10}\nfn unused := [k]() -> i32\n{\ni32 dead{2}\nexit k\n}\nexit 0"
        )
        self.assertEqual([d.name for d in program.statements], ["k", "unused"])
        self.assertEqual(program.structs[0].member_functions[0].body.statements, [])

    def test_self_feeding_variable_stays(self):
        program = optimized("i32 mut k{0}\nk := k + 1\nexit 0")
        self.assertEqual(len(program.statements), 2)

    def test_function_chain_rounds(self):
        source = Path(__file__).parent / "opt" / "unused_functions.txt"
        program = checked(source.read_text())
        for expected in (["twice", "helper"], ["twice"]):
            counter = UseCounter()
            counter.visit(program)
            Pruner(
                {key for key, reads in counter.reads.items() if reads == 0},
                {key for key, calls in counter.calls.items() if calls == 0},
            ).prune(program)
            self.assertEqual([fn.name for fn in program.functions], expected)
        module = llvm.parse_assembly(str(CodeGen().visit(remove_unused(program))))
        module.verify()
        self.assertEqual({fn.name for fn in module.functions if not fn.is_declaration},
                         {"main", "user_twice"})

    def test_mutual_recursion_and_self_recursion_stay(self):
        program = optimized(
            "fn a := () -> i32\n{\nexit b()\n}\n"
            "fn b := () -> i32\n{\nexit a()\n}\n"
            "fn self := () -> i32\n{\nexit self()\n}\nexit 0"
        )
        self.assertEqual([fn.name for fn in program.functions], ["a", "b", "self"])

    def test_nested_arguments_and_calls_from_members_and_lambdas(self):
        program = optimized(
            "struct Box\n{\ni32 x\nfn get := () -> i32\n{\nexit inner(x)\n}\n}\n"
            "fn inner := (i32 a) -> i32\n{\nexit a\n}\n"
            "fn outer := (i32 a) -> i32\n{\nexit a\n}\n"
            "fn unused := () -> i32\n{\nexit 0\n}\n"
            "fn closure := []() -> i32\n{\nexit outer(inner(3))\n}\nexit 0"
        )
        self.assertEqual([fn.name for fn in program.functions], ["inner", "outer"])
        counter = UseCounter()
        counter.visit(program)
        self.assertEqual(counter.calls[id(program.functions[0])], 2)
        self.assertEqual(counter.calls[id(program.functions[1])], 1)

    def test_implicit_member_call_does_not_keep_same_named_global(self):
        program = optimized(
            "struct Box\n{\ni32 x\nfn value := () -> i32\n{\nexit x\n}\n"
            "fn get := () -> i32\n{\nexit value()\n}\n}\n"
            "fn value := () -> i32\n{\nexit 99\n}\nBox b{4}\nexit b.get()"
        )
        self.assertEqual(program.functions, [])
        self.assertEqual([fn.name for fn in program.structs[0].member_functions], ["value", "get"])


if __name__ == "__main__":
    unittest.main()
