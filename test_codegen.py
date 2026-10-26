from pathlib import Path

from compiler import CodeGen, Parser, SemanticAnalyzer, lex


if __name__ == "__main__":
    source = Path(__file__).with_name("test_struct.txt").read_bytes()
    program = Parser(lex(source)).parse_program()
    SemanticAnalyzer().visit(program)
    generator = CodeGen()
    for struct in program.structs:
        generator.visit(struct)
    print(generator.module)
