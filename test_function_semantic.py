from pathlib import Path

from compiler import CompileError, Parser, SemanticAnalyzer, lex


if __name__ == "__main__":
    source = Path(__file__).with_name("test_function.txt").read_bytes()
    program = Parser(lex(source)).parse_program()
    try:
        SemanticAnalyzer().visit(program)
        print("Semantic analysis passed")
    except CompileError as exception:
        print(f"Semantic error: {exception}")
