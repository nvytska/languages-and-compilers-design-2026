import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from compiler import Parser, SemanticAnalyzer, UseCounter, lex


def count(source):
    program = Parser(lex(source.encode("ascii"))).parse_program()
    SemanticAnalyzer().visit(program)
    counter = UseCounter()
    counter.visit(program)
    return program, counter.reads


class UseCounterTests(unittest.TestCase):
    def test_warmup_chain(self):
        program, reads = count("i32 x{10}\ni32 y{x}\ni32 z{15}\nexit z")
        self.assertEqual([reads[id(d)] for d in program.statements], [1, 0, 1])

    def test_warmup_shadowing(self):
        program, reads = count(
            "i32 mut r{0}\ni32 x{1}\nif true\n{\n"
            "i32 x{10}\nr := x\n}\nexit r"
        )
        r, outer_x, branch = program.statements
        inner_x = branch.then_block.statements[0]
        self.assertEqual([reads[id(d)] for d in (r, outer_x, inner_x)], [1, 0, 1])

    def test_writes_do_not_read_but_self_feeding_does(self):
        program, reads = count(
            "i32 mut x{0}\nx := 5\ni32 mut k{0}\nk := k + 1\nexit 0"
        )
        self.assertEqual(reads[id(program.statements[0])], 0)
        self.assertEqual(reads[id(program.statements[2])], 1)

    def test_effects_protect_initializers_and_assignment_targets(self):
        program, reads = count(
            "fn loud := (i32 a) -> i32\n{\nprint(a)\nexit a\n}\n"
            "i32 arg{2}\ni32 unused{loud(arg) + 1}\ni32 input{read()}\n"
            "i32 mut target{0}\ntarget := loud(arg)\nexit 0"
        )
        self.assertEqual([reads[id(d)] for d in program.statements[:4]], [2, 1, 1, 1])

    def test_field_writes_and_member_receivers(self):
        program, reads = count(
            "struct Box\n{\ni32 mut x\n"
            "fn get := () -> i32\n{\nexit x\n}\n}\n"
            "Box mut dead{0}\ndead.x := 5\n"
            "Box mut protected{0}\nprotected.x := read()\n"
            "Box live{1}\nprint(live.x)\nexit live.get()"
        )
        self.assertEqual(reads[id(program.statements[0])], 0)
        self.assertEqual(reads[id(program.statements[2])], 1)
        self.assertEqual(reads[id(program.statements[4])], 2)

    def test_conditions_arguments_and_function_locals(self):
        program, reads = count(
            "fn identity := (i32 a) -> i32\n{\ni32 local{a}\nexit local\n}\n"
            "bool flag{true}\ni32 value{3}\nwhile flag\n{\n"
            "if flag\n{\nprint(identity(value))\n}\n}\nexit value"
        )
        function = program.functions[0]
        self.assertNotIn(id(function.params[0]), reads)
        self.assertEqual(reads[id(function.body.statements[0])], 1)
        self.assertEqual(reads[id(program.statements[0])], 2)
        self.assertEqual(reads[id(program.statements[1])], 2)

    def test_lowered_lambda_capture_and_callable(self):
        program, reads = count(
            "i32 k{10}\nfn add := [k](i32 y) -> i32\n{\n"
            "i32 result{k + y}\nexit result\n}\nexit add(5)"
        )
        k, closure = program.statements
        method = program.structs[0].member_functions[0]
        self.assertEqual(reads[id(k)], 1)
        self.assertEqual(reads[id(closure)], 2)  # callable read plus lambda protection
        self.assertEqual(reads[id(method.body.statements[0])], 1)

    def test_flag_positions_for_a_program_with_no_dead_variables(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.txt"
            output = Path(directory) / "output.ll"
            source.write_text("i32 x{10}\nexit x\n")
            for arguments in ([str(source), str(output)], ["--ast-checked", str(source)],
                              ["--ast", str(source)]):
                def run(args):
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "compiler.py"), *args],
                        capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    return result.stdout if arguments[0].startswith("--") else output.read_text()

                baseline = run(arguments)
                for position in range(len(arguments) + 1):
                    args = arguments[:position] + ["--remove-unused"] + arguments[position:]
                    self.assertEqual(run(args), baseline)


if __name__ == "__main__":
    unittest.main()
