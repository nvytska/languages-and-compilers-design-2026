import sys

"""Hand-written ASCII byte lexer for Practice 2, Task 1."""

class Token:
    def __init__(self, kind, text, line, column):
        self.kind = kind
        self.text = text
        self.line = line
        self.column = column

    def __repr__(self):
        return (
            f"Token(kind={self.kind!r}, "
            f"text={self.text!r}, "
            f"line={self.line}, "
            f"column={self.column})"
        )


class CompileError(ValueError):
    """A lexical error carrying the source position in its message."""


KEYWORDS = {
    "i32": "keyword",
    "mut": "keyword",
    "exit": "keyword",
}

def is_alpha(b):
    return (
        ord("a") <= b <= ord("z")
        or ord("A") <= b <= ord("Z")
        or b == ord("_")
    )


def is_digit(b):
    return ord("0") <= b <= ord("9")
def lex(data: bytes):
    lines = []
    tokens = []

    state = "START"

    start = 0
    token_line = 1
    token_col = 1

    line = 1
    col = 1

    open_braces = []
    i = 0

    while i <= len(data):
        b = data[i] if i < len(data) else None

        if state == "START":
            if b is None:
                if open_braces:
                    brace = open_braces[0]
                    raise CompileError(
                        f"line {brace.line}:{brace.column}: "
                        "'{' is not closed before the end of the line"
                    )
                break

            elif b in (32, 9):  # space, tab
                pass

            elif b == 10:  # newline
                if open_braces:
                    brace = open_braces[0]
                    raise CompileError(
                        f"line {brace.line}:{brace.column}: "
                        "'{' is not closed before the end of the line"
                    )
                tokens.append(
                    Token("endline", "\\n", line, col)
                )

                lines.append(tokens)
                tokens = []

                line += 1
                col = 0

            elif is_alpha(b):
                state = "IDENT"
                start = i
                token_line = line
                token_col = col

            elif is_digit(b):
                state = "NUMBER"
                start = i
                token_line = line
                token_col = col

            elif b == ord("{"):
                brace = Token("lbrace", "{", line, col)
                tokens.append(brace)
                open_braces.append(brace)

            elif b == ord("}"):
                if open_braces:
                    open_braces.pop()
                tokens.append(
                    Token("rbrace", "}", line, col)
                )

            elif b == ord("+"):
                tokens.append(
                    Token("operator", "+", line, col)
                )

            elif b == ord("-"):
                tokens.append(
                    Token("operator", "-", line, col)
                )

            elif b == ord("*"):
                tokens.append(
                    Token("operator", "*", line, col)
                )

            elif b == ord(":"):
                state = "COLON"
                token_line = line
                token_col = col

            else:
                char = chr(b) if b < 128 else f"0x{b:02x}"

                raise CompileError(
                    f"line {line}:{col}: "
                    f"unexpected byte '{char}'"
                )

        elif state == "IDENT":
            if (
                b is not None
                and (is_alpha(b) or is_digit(b))
            ):
                pass

            else:
                word = data[start:i].decode("ascii")

                kind = KEYWORDS.get(
                    word,
                    "identifier"
                )

                tokens.append(
                    Token(
                        kind,
                        word,
                        token_line,
                        token_col
                    )
                )

                state = "START"
                continue

        elif state == "NUMBER":
            if b is not None and is_digit(b):
                pass

            elif b is not None and is_alpha(b):
                raise CompileError(
                    f"line {token_line}:{token_col}: "
                    "letter inside number"
                )

            else:
                number = data[start:i].decode("ascii")

                tokens.append(
                    Token(
                        "number",
                        number,
                        token_line,
                        token_col
                    )
                )

                state = "START"
                continue

        elif state == "COLON":
            if b == ord("="):
                tokens.append(
                    Token(
                        "operator",
                        ":=",
                        token_line,
                        token_col
                    )
                )

                state = "START"

            else:
                raise CompileError(
                    f"line {token_line}:{token_col}: "
                    "':' must be followed by '='"
                )

        i += 1
        col += 1

    if tokens:
        lines.append(tokens)

    return lines



def error(token, message):
    raise CompileError(f"line {token.line}:{token.column}: {message}")


from dataclasses import dataclass


@dataclass
class Node:
    line: int
    column: int

    def label(self):
        raise NotImplementedError

    def children(self):
        return ()

    def dump(self, depth=0):
        return "\n".join(["  " * depth + self.label()] +
                         [child.dump(depth + 1) for child in self.children()])


@dataclass
class ProgramNode(Node):
    statements: list
    exit: "ExitNode"

    def label(self): return "Program"
    def children(self): return (*self.statements, self.exit)


class StmtNode(Node):
    pass


class ExprNode(Node):
    pass


@dataclass
class DeclNode(StmtNode):
    name: str
    mutable: bool
    init: ExprNode

    def label(self): return f"Decl {self.name} {'mut' if self.mutable else 'const'}"
    def children(self): return (self.init,)


@dataclass
class AssignNode(StmtNode):
    name: str
    value: ExprNode

    def label(self): return f"Assign {self.name}"
    def children(self): return (self.value,)


@dataclass
class ExitNode(Node):
    value: ExprNode

    def label(self): return "Exit"
    def children(self): return (self.value,)


@dataclass
class BinOpNode(ExprNode):
    op: str
    left: ExprNode
    right: ExprNode

    def label(self): return f"BinOp {self.op}"
    def children(self): return (self.left, self.right)


@dataclass
class VarNode(ExprNode):
    name: str

    def label(self): return f"Var {self.name}"


@dataclass
class ConstNode(ExprNode):
    value: int

    def label(self): return f"Const {self.value}"


class Parser:
    """Recursive descent over lexer token vectors, one statement per line."""

    def __init__(self, lines):
        self.lines = lines
        self.toks = []
        self.pos = 0
        self.end = Token("endline", "", 1, 1)

    def peek(self):
        if self.pos >= len(self.toks) or self.toks[self.pos].kind == "endline":
            return None
        return self.toks[self.pos]

    def eat(self):
        token = self.peek()
        self.pos += 1
        return token

    def expect(self, kind, text=None, message="unexpected token"):
        token = self.peek()
        if token is None or token.kind != kind or (text is not None and token.text != text):
            error(token or self.end, message)
        return self.eat()

    def parse_program(self):
        statements = []
        exit_node = None
        for tokens in self.lines:
            if not tokens or tokens[0].kind == "endline":
                continue
            self.toks, self.pos = tokens, 0
            last = tokens[-1]
            self.end = (last if last.kind == "endline" else
                        Token("endline", "", last.line, last.column + len(last.text)))
            if exit_node is not None:
                error(tokens[0], "exit must be the last statement")
            first = self.peek()
            if first.kind == "keyword" and first.text == "exit":
                exit_node = self.parse_exit()
            else:
                statements.append(self.parse_statement())
            if self.peek() is not None:
                error(self.peek(), f"extra token '{self.peek().text}'")
        if exit_node is None:
            error(self.end, "program needs an exit statement")
        return ProgramNode(1, 1, statements, exit_node)

    def parse_statement(self):
        token = self.peek()
        if token.kind == "keyword" and token.text == "i32":
            return self.parse_decl()
        if token.kind == "identifier":
            return self.parse_assign()
        error(token, "expected a declaration, assignment, or exit")

    def parse_decl(self):
        self.eat()
        mutable = self.peek() is not None and self.peek().text == "mut" and self.peek().kind == "keyword"
        if mutable:
            self.eat()
        name = self.expect("identifier", message="expected a variable name")
        self.expect("lbrace", message=f"variable '{name.text}' needs an initialiser in {{}}")
        init = self.parse_expr()
        self.expect("rbrace", message="expected '}' after initialiser")
        return DeclNode(name.line, name.column, name.text, mutable, init)

    def parse_assign(self):
        name = self.eat()
        self.expect("operator", ":=", "expected ':=' after variable name")
        return AssignNode(name.line, name.column, name.text, self.parse_expr())

    def parse_exit(self):
        token = self.eat()
        return ExitNode(token.line, token.column, self.parse_factor())

    def parse_expr(self):
        node = self.parse_term()
        while self.peek() is not None and self.peek().kind == "operator" and self.peek().text in ("+", "-"):
            op = self.eat()
            node = BinOpNode(op.line, op.column, op.text, node, self.parse_term())
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self.peek() is not None and self.peek().kind == "operator" and self.peek().text == "*":
            op = self.eat()
            node = BinOpNode(op.line, op.column, op.text, node, self.parse_factor())
        return node

    def parse_factor(self):
        token = self.peek()
        if token is None or token.kind not in ("number", "identifier"):
            error(token or self.end, "expected a constant or variable")
        self.eat()
        if token.kind == "identifier":
            return VarNode(token.line, token.column, token.text)
        digits = token.text.lstrip("0") or "0"
        if len(digits) > 10 or (len(digits) == 10 and digits > "2147483647"):
            error(token, "integer constant is outside the i32 range")
        return ConstNode(token.line, token.column, int(digits))


class CodeGen:
    def __init__(self):
        from llvmlite import ir
        import llvmlite.binding as llvm
        self.ir = ir
        self.i32, i8 = ir.IntType(32), ir.IntType(8)
        self.module = ir.Module(name="practice3")
        self.module.triple = llvm.get_default_triple()
        main = ir.Function(self.module, ir.FunctionType(self.i32, []), name="main")
        self.builder = ir.IRBuilder(main.append_basic_block("entry"))
        self.printf = ir.Function(self.module, ir.FunctionType(self.i32, [i8.as_pointer()], var_arg=True), name="printf")
        output = b"Program exit with result %d\n\0"
        fmt_type = ir.ArrayType(i8, len(output))
        self.fmt = ir.GlobalVariable(self.module, fmt_type, name="fmt")
        self.fmt.linkage = "private"
        self.fmt.global_constant = True
        self.fmt.initializer = ir.Constant(fmt_type, bytearray(output))
        self.symbols = {}

    def visit(self, node):
        return getattr(self, "visit_" + type(node).__name__)(node)

    def visit_ProgramNode(self, node):
        for statement in node.statements:
            self.visit(statement)
        self.visit(node.exit)
        return self.module

    def visit_DeclNode(self, node):
        if node.name in self.symbols:
            error(node, f"variable '{node.name}' is already declared")
        value = self.visit(node.init)
        pointer = self.builder.alloca(self.i32, name=node.name)
        self.builder.store(value, pointer)
        self.symbols[node.name] = (pointer, node.mutable)

    def variable(self, node):
        if node.name not in self.symbols:
            error(node, f"variable '{node.name}' is used before its declaration")
        return self.symbols[node.name]

    def visit_AssignNode(self, node):
        pointer, mutable = self.variable(node)
        if not mutable:
            error(node, f"cannot assign to '{node.name}': it is not mut")
        self.builder.store(self.visit(node.value), pointer)

    def visit_ExitNode(self, node):
        value = self.visit(node.value)
        fmt_pointer = self.builder.bitcast(self.fmt, self.ir.IntType(8).as_pointer())
        self.builder.call(self.printf, [fmt_pointer, value])
        self.builder.ret(self.ir.Constant(self.i32, 0))

    def visit_VarNode(self, node):
        pointer, _ = self.variable(node)
        return self.builder.load(pointer, name=f"load_{node.name}")

    def visit_ConstNode(self, node):
        return self.ir.Constant(self.i32, node.value)

    def visit_BinOpNode(self, node):
        left, right = self.visit(node.left), self.visit(node.right)
        operation = {"+": self.builder.add, "-": self.builder.sub, "*": self.builder.mul}[node.op]
        return operation(left, right, name="result")


def compile_tokens(lines):
    return CodeGen().visit(Parser(lines).parse_program())


def main():
    from pathlib import Path

    if len(sys.argv) != 3:
        print("usage: python3 compiler.py input.txt output.ll\n"
              "       python3 compiler.py --tokens input.txt\n"
              "       python3 compiler.py --ast input.txt", file=sys.stderr)
        return 1
    try:
        if sys.argv[1] == "--tokens":
            lines = lex(Path(sys.argv[2]).read_bytes())
            for tokens in lines:
                for token in tokens:
                    print(token)
        elif sys.argv[1] == "--ast":
            lines = lex(Path(sys.argv[2]).read_bytes())
            print(Parser(lines).parse_program().dump())
        else:
            lines = lex(Path(sys.argv[1]).read_bytes())
            module = compile_tokens(lines)
            # No output file is opened until every source check has succeeded.
            Path(sys.argv[2]).write_text(str(module))
    except CompileError as exception:
        print(f"compilation error: {exception}", file=sys.stderr)
        return 1
    except OSError as exception:
        print(f"compilation error: {exception}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
