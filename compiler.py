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
    "i64": "keyword",
    "bool": "keyword",
    "mut": "keyword",
    "exit": "keyword",
    "true": "keyword",
    "false": "keyword",
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
            elif b == ord("="):
                state = "EQUAL"
                token_line = line
                token_col = col

            elif b == ord("!"):
                state = "BANG"
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

        elif state == "EQUAL":
            if b == ord("="):
                tokens.append(
                    Token(
                        "operator",
                        "==",
                        token_line,
                        token_col
                    )
                )
                state = "START"
            else:
                raise CompileError(
                    f"line {token_line}:{token_col}: "
                    "expected '==' (a single '=' is not an operator)"
                )

        elif state == "BANG":
            if b == ord("="):
                tokens.append(
                    Token(
                        "operator",
                        "!=",
                        token_line,
                        token_col
                    )
                )
                state = "START"
            else:
                raise CompileError(
                    f"line {token_line}:{token_col}: "
                    "expected '!=' (a single '!' is not an operator)"
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
    type_name: str
    mutable: bool
    init: ExprNode

    def label(self):
        return f"Decl {self.name} {self.type_name} {'mut' if self.mutable else 'const'}"

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


@dataclass
class BoolNode(ExprNode):
    value: bool

    def label(self):
        return f"Bool {'true' if self.value else 'false'}"


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
        if token.kind == "keyword" and token.text in ("i32", "i64", "bool"):
            return self.parse_decl()
        if token.kind == "identifier":
            return self.parse_assign()
        error(token, "expected a declaration, assignment, or exit")

    def parse_decl(self):
        type_token = self.eat()
        mutable = self.peek() is not None and self.peek().text == "mut" and self.peek().kind == "keyword"
        if mutable:
            self.eat()
        name = self.expect("identifier", message="expected a variable name")
        self.expect("lbrace", message=f"variable '{name.text}' needs an initialiser in {{}}")
        init = self.parse_expr()
        self.expect("rbrace", message="expected '}' after initialiser")
        return DeclNode(
            name.line,
            name.column,
            name.text,
            type_token.text,
            mutable,
            init,
        )

    def parse_assign(self):
        name = self.eat()
        self.expect("operator", ":=", "expected ':=' after variable name")
        return AssignNode(name.line, name.column, name.text, self.parse_expr())

    def parse_exit(self):
        token = self.eat()
        return ExitNode(token.line, token.column, self.parse_factor())

    def parse_expr(self):
        node = self.parse_arith()
        if (
            self.peek() is not None
            and self.peek().kind == "operator"
            and self.peek().text in ("==", "!=")
        ):
            op = self.eat()
            node = BinOpNode(
                op.line,
                op.column,
                op.text,
                node,
                self.parse_arith(),
            )
        return node

    def parse_arith(self):
        node = self.parse_term()
        while (
            self.peek() is not None
            and self.peek().kind == "operator"
            and self.peek().text in ("+", "-")
        ):
            op = self.eat()
            node = BinOpNode(
                op.line,
                op.column,
                op.text,
                node,
                self.parse_term(),
            )
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self.peek() is not None and self.peek().kind == "operator" and self.peek().text == "*":
            op = self.eat()
            node = BinOpNode(op.line, op.column, op.text, node, self.parse_factor())
        return node

    def parse_factor(self):
        token = self.peek()
        if token is None:
            error(token or self.end, "expected a constant or variable")

        if token.kind == "identifier":
            self.eat()
            return VarNode(token.line, token.column, token.text)

        if token.kind == "keyword" and token.text in ("true", "false"):
            self.eat()
            return BoolNode(
                token.line,
                token.column,
                token.text == "true",
            )

        if token.kind == "number":
            self.eat()
            digits = token.text.lstrip("0") or "0"
            return ConstNode(
                token.line,
                token.column,
                int(digits),
            )

        error(token, "expected a constant or variable")


class SemanticChecker:
    def __init__(self):
        self.symbols = {}

    def visit(self, node):
        return getattr(
            self,
            "visit_" + type(node).__name__,
        )(node)

    def visit_ProgramNode(self, node):
        for statement in node.statements:
            self.visit(statement)
        self.visit(node.exit)
        return node

    def visit_ConstNode(self, node):
        if node.value <= 2147483647:
            node.type = "i32"
        elif node.value <= 9223372036854775807:
            node.type = "i64"
        else:
            error(
                node,
                f"constant {node.value} does not fit in i64",
            )
        return node.type

    def visit_BoolNode(self, node):
        node.type = "bool"
        return node.type

    def is_integer(self, type_name):
        return type_name in ("i32", "i64")

    def visit_VarNode(self, node):
        if node.name not in self.symbols:
            error(
                node,
                f"variable '{node.name}' is used before its declaration",
            )
        node.decl = self.symbols[node.name]
        node.type = node.decl.type_name
        return node.type

    def visit_BinOpNode(self, node):
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)

        if node.op in ("+", "-", "*"):
            if not self.is_integer(left_type):
                error(
                    node,
                    f"cannot apply '{node.op}' to {left_type}",
                )
            if not self.is_integer(right_type):
                error(
                    node,
                    f"cannot apply '{node.op}' to {right_type}",
                )
            if left_type == "i64" or right_type == "i64":
                node.type = "i64"
            else:
                node.type = "i32"
            return node.type

        if node.op in ("==", "!="):
            both_integers = (
                self.is_integer(left_type)
                and self.is_integer(right_type)
            )
            both_bools = (
                left_type == "bool"
                and right_type == "bool"
            )
            if both_integers or both_bools:
                node.type = "bool"
                return node.type
            error(
                node,
                f"cannot compare {left_type} with {right_type}",
            )

    def check_assignable(self, expr, want, at, what):
        have = expr.type
        if have == want:
            return
        if have == "i32" and want == "i64":
            return
        error(
            at,
            f"cannot {what} of type {want} "
            f"with a value of type {have}",
        )

    def visit_DeclNode(self, node):
        if node.name in self.symbols:
            error(
                node,
                f"variable '{node.name}' is already declared",
            )
        self.visit(node.init)
        self.check_assignable(
            node.init,
            node.type_name,
            node,
            f"initialise '{node.name}'",
        )
        self.symbols[node.name] = node

    def visit_AssignNode(self, node):
        if node.name not in self.symbols:
            error(
                node,
                f"variable '{node.name}' is used before its declaration",
            )
        decl = self.symbols[node.name]
        node.decl = decl
        if not decl.mutable:
            error(
                node,
                f"cannot assign to '{node.name}': it is not mut",
            )
        self.visit(node.value)
        self.check_assignable(
            node.value,
            decl.type_name,
            node,
            f"assign to '{node.name}'",
        )

    def visit_ExitNode(self, node):
        value_type = self.visit(node.value)
        if value_type not in ("i32", "i64", "bool"):
            error(
                node,
                f"cannot exit with value of type {value_type}",
            )


class CodeGen:
    def __init__(self):
        from llvmlite import ir
        import llvmlite.binding as llvm
        self.ir = ir
        self.i32 = ir.IntType(32)
        self.i64 = ir.IntType(64)
        self.i1 = ir.IntType(1)
        i8 = ir.IntType(8)
        self.module = ir.Module(name="practice3")
        self.module.triple = llvm.get_default_triple()
        main = ir.Function(self.module, ir.FunctionType(self.i32, []), name="main")
        self.builder = ir.IRBuilder(main.append_basic_block("entry"))
        self.printf = ir.Function(self.module, ir.FunctionType(self.i32, [i8.as_pointer()], var_arg=True), name="printf")
        output = b"Program exit with result %lld\n\0"
        fmt_type = ir.ArrayType(i8, len(output))
        self.fmt = ir.GlobalVariable(self.module, fmt_type, name="fmt")
        self.fmt.linkage = "private"
        self.fmt.global_constant = True
        self.fmt.initializer = ir.Constant(fmt_type, bytearray(output))

        true_text = b"true\0"
        true_type = ir.ArrayType(i8, len(true_text))
        self.true_str = ir.GlobalVariable(
            self.module,
            true_type,
            name="true_str",
        )
        self.true_str.linkage = "private"
        self.true_str.global_constant = True
        self.true_str.initializer = ir.Constant(
            true_type,
            bytearray(true_text),
        )

        false_text = b"false\0"
        false_type = ir.ArrayType(i8, len(false_text))
        self.false_str = ir.GlobalVariable(
            self.module,
            false_type,
            name="false_str",
        )
        self.false_str.linkage = "private"
        self.false_str.global_constant = True
        self.false_str.initializer = ir.Constant(
            false_type,
            bytearray(false_text),
        )

        bool_output = b"Program exit with result %s\n\0"
        bool_fmt_type = ir.ArrayType(i8, len(bool_output))
        self.bool_fmt = ir.GlobalVariable(
            self.module,
            bool_fmt_type,
            name="bool_fmt",
        )
        self.bool_fmt.linkage = "private"
        self.bool_fmt.global_constant = True
        self.bool_fmt.initializer = ir.Constant(
            bool_fmt_type,
            bytearray(bool_output),
        )
        self.variables = {}

    def visit(self, node):
        return getattr(self, "visit_" + type(node).__name__)(node)

    def llvm_type(self, type_name):
        return {
            "i32": self.i32,
            "i64": self.i64,
            "bool": self.i1,
        }[type_name]

    def coerce(self, value, have, want):
        if have == "i32" and want == "i64":
            return self.builder.sext(
                value,
                self.i64,
                name="wide",
            )
        return value

    def visit_ProgramNode(self, node):
        for statement in node.statements:
            self.visit(statement)
        self.visit(node.exit)
        return self.module

    def visit_DeclNode(self, node):
        value = self.visit(node.init)
        value = self.coerce(
            value,
            node.init.type,
            node.type_name,
        )
        pointer = self.builder.alloca(
            self.llvm_type(node.type_name),
            name=node.name,
        )
        self.builder.store(value, pointer)
        self.variables[id(node)] = pointer

    def visit_AssignNode(self, node):
        pointer = self.variables[id(node.decl)]
        value = self.visit(node.value)
        value = self.coerce(
            value,
            node.value.type,
            node.decl.type_name,
        )
        self.builder.store(value, pointer)

    def visit_ExitNode(self, node):
        value = self.visit(node.value)
        if node.value.type in ("i32", "i64"):
            value = self.coerce(
                value,
                node.value.type,
                "i64",
            )
            fmt_pointer = self.builder.bitcast(
                self.fmt,
                self.ir.IntType(8).as_pointer(),
            )
            self.builder.call(
                self.printf,
                [fmt_pointer, value],
            )
        else:
            true_pointer = self.builder.bitcast(
                self.true_str,
                self.ir.IntType(8).as_pointer(),
            )
            false_pointer = self.builder.bitcast(
                self.false_str,
                self.ir.IntType(8).as_pointer(),
            )
            text = self.builder.select(
                value,
                true_pointer,
                false_pointer,
                name="bool_text",
            )
            fmt_pointer = self.builder.bitcast(
                self.bool_fmt,
                self.ir.IntType(8).as_pointer(),
            )
            self.builder.call(
                self.printf,
                [fmt_pointer, text],
            )
        self.builder.ret(self.ir.Constant(self.i32, 0))

    def visit_VarNode(self, node):
        pointer = self.variables[id(node.decl)]
        return self.builder.load(
            pointer,
            name=f"load_{node.name}",
        )

    def visit_ConstNode(self, node):
        return self.ir.Constant(
            self.llvm_type(node.type),
            node.value,
        )

    def visit_BoolNode(self, node):
        return self.ir.Constant(
            self.i1,
            1 if node.value else 0,
        )

    def visit_BinOpNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        left_type = node.left.type
        right_type = node.right.type

        if node.op in ("+", "-", "*"):
            result_type = node.type
            left = self.coerce(
                left,
                left_type,
                result_type,
            )
            right = self.coerce(
                right,
                right_type,
                result_type,
            )
            operation = {
                "+": self.builder.add,
                "-": self.builder.sub,
                "*": self.builder.mul,
            }[node.op]
            return operation(
                left,
                right,
                name="result",
            )

        comparison_type = (
            "i64"
            if left_type == "i64" or right_type == "i64"
            else left_type
        )
        left = self.coerce(
            left,
            left_type,
            comparison_type,
        )
        right = self.coerce(
            right,
            right_type,
            comparison_type,
        )
        return self.builder.icmp_signed(
            node.op,
            left,
            right,
            name="compare",
        )


def compile_tokens(lines):
    tree = Parser(lines).parse_program()
    SemanticChecker().visit(tree)
    return CodeGen().visit(tree)


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
