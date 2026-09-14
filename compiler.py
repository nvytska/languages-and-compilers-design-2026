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


class LineParser:
    """Consume a single statement using only lexer tokens."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0
        last = tokens[-1]
        self.end = (last if last.kind == "endline" else
                    Token("endline", "", last.line, last.column + len(last.text)))

    def peek(self):
        return self.tokens[self.index] if self.index < len(self.tokens) else self.end

    def take(self, kind=None, text=None, message="unexpected token"):
        token = self.peek()
        if token.kind == "endline" or (kind and token.kind != kind) or (text and token.text != text):
            error(token, message)
        self.index += 1
        return token

    def finish(self):
        token = self.peek()
        if token.kind != "endline":
            error(token, f"extra token '{token.text}'")


def compile_tokens(lines):
    from llvmlite import ir
    import llvmlite.binding as llvm

    i32, i8 = ir.IntType(32), ir.IntType(8)
    module = ir.Module(name="practice2")
    module.triple = llvm.get_default_triple()
    main_function = ir.Function(module, ir.FunctionType(i32, []), name="main")
    builder = ir.IRBuilder(main_function.append_basic_block("entry"))
    printf = ir.Function(module, ir.FunctionType(i32, [i8.as_pointer()], var_arg=True), name="printf")
    text = b"Program exit with result %d\n\0"
    fmt_type = ir.ArrayType(i8, len(text))
    fmt = ir.GlobalVariable(module, fmt_type, name="fmt")
    fmt.linkage = "private"
    fmt.global_constant = True
    fmt.initializer = ir.Constant(fmt_type, bytearray(text))
    symbols = {}
    found_exit = False
    last_position = Token("endline", "", 1, 1)

    def variable(token):
        if token.text not in symbols:
            error(token, f"variable '{token.text}' is used before its declaration")
        return symbols[token.text]

    def operand(parser):
        token = parser.take(message="expected a constant or variable")
        if token.kind == "number":
            # Compare text before conversion so arbitrarily long literals are diagnosed.
            digits = token.text.lstrip("0") or "0"
            if len(digits) > 10 or (len(digits) == 10 and digits > "2147483647"):
                error(token, "integer constant is outside the i32 range")
            return ir.Constant(i32, int(digits))
        if token.kind == "identifier":
            pointer, _ = variable(token)
            return builder.load(pointer, name=f"load_{token.text}")
        error(token, "expected a constant or variable")

    def expression(parser):
        left = operand(parser)
        token = parser.peek()
        if token.kind == "operator" and token.text in ("+", "-", "*"):
            parser.take()
            right = operand(parser)
            operation = {"+": builder.add, "-": builder.sub, "*": builder.mul}[token.text]
            return operation(left, right, name="result")
        return left

    for tokens in lines:
        if not tokens:
            continue
        parser = LineParser(tokens)
        last_position = parser.end
        first = parser.peek()
        if first.kind == "endline":
            continue
        if found_exit:
            error(first, "exit must be the last statement")
        if first.kind == "keyword" and first.text == "i32":
            parser.take()
            mutable = parser.peek().kind == "keyword" and parser.peek().text == "mut"
            if mutable:
                parser.take()
            name = parser.take("identifier", message="expected a variable name")
            if name.text in symbols:
                error(name, f"variable '{name.text}' is already declared")
            parser.take("lbrace", message=f"variable '{name.text}' needs an initialiser in {{}}")
            value = expression(parser)
            parser.take("rbrace", message="expected '}' after initialiser")
            parser.finish()
            pointer = builder.alloca(i32, name=name.text)
            builder.store(value, pointer)
            symbols[name.text] = (pointer, mutable)
        elif first.kind == "identifier":
            name = parser.take()
            parser.take("operator", ":=", "expected ':=' after variable name")
            pointer, mutable = variable(name)
            if not mutable:
                error(name, f"cannot assign to '{name.text}': it is not mut")
            value = expression(parser)
            parser.finish()
            builder.store(value, pointer)
        elif first.kind == "keyword" and first.text == "exit":
            parser.take()
            value = operand(parser)
            parser.finish()
            fmt_pointer = builder.bitcast(fmt, i8.as_pointer())
            builder.call(printf, [fmt_pointer, value])
            builder.ret(ir.Constant(i32, 0))
            found_exit = True
        else:
            error(first, "expected a declaration, assignment, or exit")
    if not found_exit:
        error(last_position, "program needs an exit statement")
    return module


def main():
    from pathlib import Path

    if len(sys.argv) != 3:
        print("usage: python3 compiler.py input.txt output.ll\n"
              "       python3 compiler.py --tokens input.txt", file=sys.stderr)
        return 1
    try:
        if sys.argv[1] == "--tokens":
            lines = lex(Path(sys.argv[2]).read_bytes())
            for tokens in lines:
                for token in tokens:
                    print(token)
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
