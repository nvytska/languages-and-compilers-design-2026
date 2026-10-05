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
    "if": "keyword",
    "else": "keyword",
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

    i = 0

    while i <= len(data):
        b = data[i] if i < len(data) else None

        if state == "START":
            if b is None:
                break

            elif b in (32, 9):  # space, tab
                pass

            elif b == 10:  # newline
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
                tokens.append(
                    Token("lbrace", "{", line, col)
                )

            elif b == ord("}"):
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
                tokens.append(
                    Token(
                        "operator",
                        "!",
                        token_line,
                        token_col
                    )
                )
                state = "START"
                continue

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
        return (
            f"Decl {self.name} {self.type_name} "
            f"{'mut' if self.mutable else 'const'}"
        )

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
class BlockNode(Node):
    statements: list
    exit: "ExitNode | None"

    def label(self):
        return "Block"

    def children(self):
        if self.exit is not None:
            return (*self.statements, self.exit)
        return tuple(self.statements)


@dataclass
class IfNode(StmtNode):
    condition: ExprNode
    then_block: BlockNode
    else_block: "BlockNode | None"

    def label(self):
        return "If"

    def children(self):
        if self.else_block is not None:
            return (self.condition, self.then_block, self.else_block)
        return (self.condition, self.then_block)


@dataclass
class NotNode(ExprNode):
    value: ExprNode

    def label(self):
        return "Not"

    def children(self):
        return (self.value,)


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
        self.line_pos = 0
        self.toks = []
        self.pos = 0
        self.end = Token("endline", "", 1, 1)

    def peek_line(self):
        pos = self.line_pos
        while pos < len(self.lines):
            tokens = self.lines[pos]
            if tokens and not (
                len(tokens) == 1 and tokens[0].kind == "endline"
            ):
                return tokens
            pos += 1
        return None

    def next_line(self):
        while self.line_pos < len(self.lines):
            tokens = self.lines[self.line_pos]
            self.line_pos += 1
            if not tokens or (
                len(tokens) == 1 and tokens[0].kind == "endline"
            ):
                continue
            self.toks = tokens
            self.pos = 0
            last = tokens[-1]
            self.end = (
                last
                if last.kind == "endline"
                else Token(
                    "endline",
                    "",
                    last.line,
                    last.column + len(last.text),
                )
            )
            return tokens
        return None

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
        while self.peek_line() is not None:
            self.next_line()
            first = self.peek()
            if first.kind == "keyword" and first.text == "exit":
                exit_node = self.parse_exit()
                if self.peek() is not None:
                    error(self.peek(), f"extra token '{self.peek().text}'")
                if self.peek_line() is not None:
                    next_tokens = self.peek_line()
                    error(next_tokens[0], "exit must be the last statement")
                break
            statements.append(self.parse_statement())
            if self.peek() is not None:
                error(self.peek(), f"extra token '{self.peek().text}'")
        if exit_node is None:
            error(self.end, "program needs an exit statement")
        return ProgramNode(1, 1, statements, exit_node)

    def parse_statement(self):
        token = self.peek()
        if (
            token.kind == "keyword"
            and token.text in ("i32", "i64", "bool")
        ):
            return self.parse_decl()
        if token.kind == "keyword" and token.text == "if":
            return self.parse_if()
        if token.kind == "identifier":
            return self.parse_assign()
        error(token, "expected a declaration, assignment, or if")

    def parse_if(self):
        if_token = self.expect("keyword", "if")
        condition = self.parse_expr()
        if self.peek() is not None:
            error(
                self.peek(),
                f"unexpected '{self.peek().text}' after the statement",
            )

        block_line = self.next_line()
        if block_line is None:
            error(
                self.end,
                "expected '{' on its own line after 'if'",
            )
        if not (
            len(block_line) >= 1
            and block_line[0].kind == "lbrace"
            and self.peek() is not None
            and self.peek().kind == "lbrace"
        ):
            got = self.peek()
            error(
                got or self.end,
                "expected '{' on its own line after 'if'",
            )
        self.eat()
        if self.peek() is not None:
            error(
                self.peek(),
                f"unexpected '{self.peek().text}' after '{{'",
            )

        then_block = self.parse_block(if_token)
        else_block = None
        next_tokens = self.peek_line()
        if (
            next_tokens is not None
            and next_tokens[0].kind == "keyword"
            and next_tokens[0].text == "else"
        ):
            self.next_line()
            else_token = self.expect("keyword", "else")
            if self.peek() is not None:
                error(
                    self.peek(),
                    f"unexpected '{self.peek().text}' after 'else'",
                )

            block_line = self.next_line()
            if block_line is None:
                error(
                    self.end,
                    "expected '{' on its own line after 'else'",
                )
            if not (
                block_line[0].kind == "lbrace"
                and self.peek() is not None
                and self.peek().kind == "lbrace"
            ):
                got = self.peek()
                error(
                    got or self.end,
                    "expected '{' on its own line after 'else'",
                )
            self.eat()
            if self.peek() is not None:
                error(
                    self.peek(),
                    f"unexpected '{self.peek().text}' after '{{'",
                )
            else_block = self.parse_block(else_token)

        return IfNode(
            if_token.line,
            if_token.column,
            condition,
            then_block,
            else_block,
        )

    def parse_block(self, owner):
        statements = []
        exit_node = None
        while True:
            tokens = self.next_line()
            if tokens is None:
                error(owner, "'{' is never closed")
            first = self.peek()
            if first.kind == "rbrace":
                self.eat()
                if self.peek() is not None:
                    error(
                        self.peek(),
                        f"unexpected '{self.peek().text}' after '}}'",
                    )
                if not statements and exit_node is None:
                    error(first, "empty block")
                return BlockNode(
                    owner.line,
                    owner.column,
                    statements,
                    exit_node,
                )
            if exit_node is not None:
                error(first, "exit must be the last statement in a block")
            if first.kind == "keyword" and first.text == "exit":
                exit_node = self.parse_exit()
            else:
                statements.append(self.parse_statement())
            if self.peek() is not None:
                error(self.peek(), f"extra token '{self.peek().text}'")

    def parse_decl(self):
        type_token = self.eat()
        mutable = (
            self.peek() is not None
            and self.peek().kind == "keyword"
            and self.peek().text == "mut"
        )
        if mutable:
            self.eat()
        name = self.expect(
            "identifier",
            message="expected a variable name",
        )
        self.expect(
            "lbrace",
            message=f"variable '{name.text}' needs an initialiser in {{}}",
        )
        init = self.parse_expr()
        if self.peek() is None:
            previous = self.toks[self.pos - 1]
            end_of_line = Token(
                "endline",
                "",
                previous.line,
                previous.column + len(previous.text) - 1,
            )
            error(end_of_line, "expected '}', found end of line")
        self.expect(
            "rbrace",
            message="expected '}' after initialiser",
        )
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
        node = self.parse_arithmetic()
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
                self.parse_arithmetic(),
            )
        return node

    def parse_arithmetic(self):
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
        if (
            token is not None
            and token.kind == "operator"
            and token.text == "!"
        ):
            op = self.eat()
            value = self.parse_factor()
            return NotNode(
                op.line,
                op.column,
                value,
            )
        if token is None or token.kind not in (
            "number",
            "identifier",
            "keyword",
        ):
            error(
                token or self.end,
                "expected a constant or variable",
            )
        self.eat()
        if token.kind == "identifier":
            return VarNode(
                token.line,
                token.column,
                token.text,
            )
        if token.kind == "keyword":
            if token.text == "true":
                return BoolNode(
                    token.line,
                    token.column,
                    True,
                )
            if token.text == "false":
                return BoolNode(
                    token.line,
                    token.column,
                    False,
                )
            error(token, "expected a constant or variable")
        digits = token.text.lstrip("0") or "0"
        if (
            len(digits) > 19
            or (
                len(digits) == 19
                and digits > "9223372036854775807"
            )
        ):
            error(
                token,
                f"constant {token.text} does not fit in i64",
            )
        return ConstNode(
            token.line,
            token.column,
            int(digits),
        )


class SemanticAnalyzer:
    def __init__(self):
        self.scopes = [{}]

    def visit(self, node):
        return getattr(
            self,
            "visit_" + type(node).__name__,
        )(node)

    def lookup(self, node, name):
        for frame in reversed(self.scopes):
            if name in frame:
                return frame[name]
        raise CompileError(
            f"line {node.line}:{node.column}: "
            f"variable '{name}' is used before its declaration"
        )

    def visit_ProgramNode(self, node):
        for statement in node.statements:
            self.visit(statement)
        self.visit(node.exit)

    def visit_BlockNode(self, node):
        self.scopes.append({})
        for statement in node.statements:
            self.visit(statement)
        if node.exit is not None:
            self.visit(node.exit)
        self.scopes.pop()

    def visit_DeclNode(self, node):
        frame = self.scopes[-1]
        if node.name in frame:
            raise CompileError(
                f"line {node.line}:{node.column}: "
                f"variable '{node.name}' is already declared in this block"
            )
        init_type = self.visit(node.init)
        if init_type != node.type_name:
            if not (node.type_name == "i64" and init_type == "i32"):
                raise CompileError(
                    f"line {node.line}:{node.column}: "
                    f"cannot initialise '{node.name}' of type {node.type_name} "
                    f"with a value of type {init_type}"
                )
        frame[node.name] = node

    def visit_VarNode(self, node):
        node.decl = self.lookup(node, node.name)
        return node.decl.type_name

    def visit_AssignNode(self, node):
        decl = self.lookup(node, node.name)
        node.decl = decl
        if not decl.mutable:
            raise CompileError(
                f"line {node.line}:{node.column}: "
                f"cannot assign to '{node.name}': it is not mut"
            )
        value_type = self.visit(node.value)
        if value_type != decl.type_name:
            if not (decl.type_name == "i64" and value_type == "i32"):
                raise CompileError(
                    f"line {node.line}:{node.column}: "
                    f"cannot assign to '{node.name}' of type {decl.type_name} "
                    f"with a value of type {value_type}"
                )

    def visit_ConstNode(self, node):
        if node.value <= 2147483647:
            return "i32"
        return "i64"

    def visit_BoolNode(self, node):
        return "bool"

    def visit_BinOpNode(self, node):
        left_type = self.visit(node.left)
        right_type = self.visit(node.right)
        if node.op in ("+", "-", "*"):
            if left_type == "bool":
                raise CompileError(
                    f"line {node.line}:{node.column}: "
                    f"cannot apply '{node.op}' to bool"
                )
            if right_type == "bool":
                raise CompileError(
                    f"line {node.line}:{node.column}: "
                    f"cannot apply '{node.op}' to bool"
                )
            if left_type == "i64" or right_type == "i64":
                return "i64"
            return "i32"
        if node.op in ("==", "!="):
            if left_type == right_type:
                return "bool"
            if {left_type, right_type} == {"i32", "i64"}:
                return "bool"
            raise CompileError(
                f"line {node.line}:{node.column}: "
                f"cannot compare {left_type} with {right_type}"
            )

    def visit_ExitNode(self, node):
        self.visit(node.value)

    def visit_IfNode(self, node):
        condition_type = self.visit(node.condition)
        if condition_type != "bool":
            raise CompileError(
                f"line {node.line}:{node.column}: "
                f"the condition of 'if' must be bool, got {condition_type}"
            )
        self.visit(node.then_block)
        if node.else_block is not None:
            self.visit(node.else_block)

    def visit_NotNode(self, node):
        value_type = self.visit(node.value)
        if value_type != "bool":
            raise CompileError(
                f"line {node.line}:{node.column}: "
                f"cannot apply '!' to {value_type}"
            )
        return "bool"


class CodeGen:
    def __init__(self):
        from llvmlite import ir
        import llvmlite.binding as llvm
        self.ir = ir
        self.i32 = ir.IntType(32)
        self.i64 = ir.IntType(64)
        self.i1 = ir.IntType(1)
        i8 = ir.IntType(8)
        self.module = ir.Module(name="practice5")
        self.module.triple = llvm.get_default_triple()
        self.function = ir.Function(
            self.module,
            ir.FunctionType(self.i32, []),
            name="main",
        )
        self.entry = self.function.append_basic_block("entry")
        self.builder = ir.IRBuilder(self.entry)
        self.printf = ir.Function(self.module, ir.FunctionType(self.i32, [i8.as_pointer()], var_arg=True), name="printf")
        output = b"Program exit with result %lld\n\0"
        fmt_type = ir.ArrayType(i8, len(output))
        self.fmt = ir.GlobalVariable(self.module, fmt_type, name="fmt")
        self.fmt.linkage = "private"
        self.fmt.global_constant = True
        self.fmt.initializer = ir.Constant(fmt_type, bytearray(output))

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

        true_text = b"true\0"
        true_type = ir.ArrayType(i8, len(true_text))
        self.true_text = ir.GlobalVariable(
            self.module,
            true_type,
            name="true_text",
        )
        self.true_text.linkage = "private"
        self.true_text.global_constant = True
        self.true_text.initializer = ir.Constant(
            true_type,
            bytearray(true_text),
        )

        false_text = b"false\0"
        false_type = ir.ArrayType(i8, len(false_text))
        self.false_text = ir.GlobalVariable(
            self.module,
            false_type,
            name="false_text",
        )
        self.false_text.linkage = "private"
        self.false_text.global_constant = True
        self.false_text.initializer = ir.Constant(
            false_type,
            bytearray(false_text),
        )
        self.slots = {}

    def llvm_type(self, type_name):
        return {
            "i32": self.i32,
            "i64": self.i64,
            "bool": self.i1,
        }[type_name]

    def create_entry_alloca(self, decl):
        saved_block = self.builder.block
        entry_builder = self.ir.IRBuilder(self.entry)
        if self.entry.instructions:
            entry_builder.position_before(
                self.entry.instructions[0]
            )
        else:
            entry_builder.position_at_end(self.entry)
        pointer = entry_builder.alloca(
            self.llvm_type(decl.type_name),
            name=decl.name,
        )
        self.builder.position_at_end(saved_block)
        return pointer

    def visit(self, node):
        return getattr(self, "visit_" + type(node).__name__)(node)

    def visit_ProgramNode(self, node):
        for statement in node.statements:
            if self.builder.block.is_terminated:
                break
            self.visit(statement)
        if not self.builder.block.is_terminated:
            self.visit(node.exit)
        return self.module

    def visit_DeclNode(self, node):
        value = self.visit(node.init)
        target_type = self.llvm_type(node.type_name)
        if value.type != target_type:
            if value.type == self.i32 and target_type == self.i64:
                value = self.builder.sext(
                    value,
                    self.i64,
                    name="widen",
                )
        pointer = self.create_entry_alloca(node)
        self.builder.store(value, pointer)
        self.slots[id(node)] = pointer

    def visit_AssignNode(self, node):
        pointer = self.slots[id(node.decl)]
        value = self.visit(node.value)
        target_type = self.llvm_type(node.decl.type_name)
        if value.type != target_type:
            if value.type == self.i32 and target_type == self.i64:
                value = self.builder.sext(
                    value,
                    self.i64,
                    name="widen",
                )
        self.builder.store(value, pointer)

    def visit_ExitNode(self, node):
        value = self.visit(node.value)
        i8_ptr = self.ir.IntType(8).as_pointer()
        if value.type == self.i1:
            fmt_pointer = self.builder.bitcast(
                self.bool_fmt,
                i8_ptr,
            )
            true_pointer = self.builder.bitcast(
                self.true_text,
                i8_ptr,
            )
            false_pointer = self.builder.bitcast(
                self.false_text,
                i8_ptr,
            )
            text_pointer = self.builder.select(
                value,
                true_pointer,
                false_pointer,
                name="bool_text",
            )
            self.builder.call(
                self.printf,
                [fmt_pointer, text_pointer],
            )
        else:
            if value.type == self.i32:
                value = self.builder.sext(
                    value,
                    self.i64,
                    name="exit_to_i64",
                )
            fmt_pointer = self.builder.bitcast(
                self.fmt,
                i8_ptr,
            )
            self.builder.call(
                self.printf,
                [fmt_pointer, value],
            )
        self.builder.ret(
            self.ir.Constant(self.i32, 0)
        )

    def visit_VarNode(self, node):
        pointer = self.slots[id(node.decl)]
        return self.builder.load(
            pointer,
            name=f"load_{node.name}",
        )

    def visit_ConstNode(self, node):
        if node.value <= 2147483647:
            return self.ir.Constant(
                self.i32,
                node.value,
            )
        return self.ir.Constant(
            self.i64,
            node.value,
        )

    def visit_BoolNode(self, node):
        return self.ir.Constant(
            self.i1,
            1 if node.value else 0,
        )

    def visit_NotNode(self, node):
        value = self.visit(node.value)
        return self.builder.xor(
            value,
            self.ir.Constant(self.i1, 1),
            name="not",
        )

    def visit_BinOpNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left.type != right.type:
            if left.type == self.i32 and right.type == self.i64:
                left = self.builder.sext(left, self.i64, name="widen")
            elif left.type == self.i64 and right.type == self.i32:
                right = self.builder.sext(right, self.i64, name="widen")
        if node.op == "+":
            return self.builder.add(left, right, name="add")
        if node.op == "-":
            return self.builder.sub(left, right, name="sub")
        if node.op == "*":
            return self.builder.mul(left, right, name="mul")
        if node.op == "==":
            return self.builder.icmp_signed(
                "==",
                left,
                right,
                name="cmp",
            )
        if node.op == "!=":
            return self.builder.icmp_signed(
                "!=",
                left,
                right,
                name="cmp",
            )
        raise RuntimeError(f"unsupported operator {node.op}")

    def visit_BlockNode(self, node):
        for statement in node.statements:
            if self.builder.block.is_terminated:
                break
            self.visit(statement)
        if (
            node.exit is not None
            and not self.builder.block.is_terminated
        ):
            self.visit(node.exit)

    def visit_IfNode(self, node):
        condition = self.visit(node.condition)
        then_bb = self.function.append_basic_block("then")
        else_bb = (
            self.function.append_basic_block("else")
            if node.else_block is not None
            else None
        )
        merge_bb = self.function.append_basic_block("merge")
        self.builder.cbranch(
            condition,
            then_bb,
            else_bb if else_bb is not None else merge_bb,
        )

        self.builder.position_at_end(then_bb)
        self.visit(node.then_block)
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_bb)

        if else_bb is not None:
            self.builder.position_at_end(else_bb)
            self.visit(node.else_block)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_bb)

        self.builder.position_at_end(merge_bb)


def compile_tokens(lines):
    program = Parser(lines).parse_program()
    SemanticAnalyzer().visit(program)
    return CodeGen().visit(program)


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
