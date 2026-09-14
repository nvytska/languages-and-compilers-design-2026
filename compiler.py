import sys
import re

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



def compilation_error(line_number, message):
    print(
        f"compilation error: line {line_number}: {message}",
        file=sys.stderr
    )
    sys.exit(1)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--tokens":
        from pathlib import Path

        try:
            token_lines = lex(Path(sys.argv[2]).read_bytes())
        except CompileError as error:
            print(f"compilation error: {error}", file=sys.stderr)
            sys.exit(1)
        for token_line in token_lines:
            for token in token_line:
                print(token)
        return

    from llvmlite import ir
    import llvmlite.binding as llvm

    I32 = ir.IntType(32)
    I8 = ir.IntType(8)

    if len(sys.argv) != 3:
        print(
            "usage: python3 compiler.py input.txt output.ll",
            file=sys.stderr
        )
        sys.exit(1)


    input_path = sys.argv[1]
    output_path = sys.argv[2]


    module = ir.Module(name="practice1")
    module.triple = llvm.get_default_triple()


    main_type = ir.FunctionType(I32, [])
    main = ir.Function(module, main_type, name="main")

    entry = main.append_basic_block("entry")
    builder = ir.IRBuilder(entry)


    printf_type = ir.FunctionType(
        I32,
        [ir.PointerType(I8)],
        var_arg=True
    )

    printf = ir.Function(
        module,
        printf_type,
        name="printf"
    )


    text = b"Program exit with result %d\n\0"

    fmt_type = ir.ArrayType(I8, len(text))

    fmt = ir.GlobalVariable(
        module,
        fmt_type,
        name="fmt"
    )

    fmt.linkage = "private"
    fmt.global_constant = True

    fmt.initializer = ir.Constant(
        fmt_type,
        bytearray(text)
    )


    symbols = {}


    def get_value(token, line_number):
        if re.fullmatch(r"-?\d+", token):
            return ir.Constant(I32, int(token))

        if token in symbols:
            return builder.load(
                symbols[token],
                name=f"load_{token}"
            )

        compilation_error(
            line_number,
            f"undeclared variable '{token}'"
        )


    with open(input_path, "r") as f:
        lines = f.readlines()


    found_exit = False


    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line:
            continue

        # int x
        declaration = re.fullmatch(
            r"int\s+([A-Za-z_][A-Za-z0-9_]*)",
            line
        )

        if declaration:
            name = declaration.group(1)

            if name in ("int", "exit"):
                compilation_error(
                    line_number,
                    f"reserved name '{name}'"
                )

            if name in symbols:
                compilation_error(
                    line_number,
                    f"variable '{name}' already declared"
                )

            symbols[name] = builder.alloca(
                I32,
                name=name
            )

            continue

        # x := ...
        assignment = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_]*)\s*:=\s*(.+)",
            line
        )

        if assignment:
            target = assignment.group(1)
            expression = assignment.group(2).strip()

            if target not in symbols:
                compilation_error(
                    line_number,
                    f"undeclared variable '{target}'"
                )

            operation = re.fullmatch(
                r"([A-Za-z_][A-Za-z0-9_]*|-?\d+)\s*"
                r"([+\-*])\s*"
                r"([A-Za-z_][A-Za-z0-9_]*|-?\d+)",
                expression
            )

            if operation:
                left_token = operation.group(1)
                operator = operation.group(2)
                right_token = operation.group(3)

                left = get_value(
                    left_token,
                    line_number
                )

                right = get_value(
                    right_token,
                    line_number
                )

                if operator == "+":
                    result = builder.add(
                        left,
                        right,
                        name="addtmp"
                    )

                elif operator == "-":
                    result = builder.sub(
                        left,
                        right,
                        name="subtmp"
                    )

                else:
                    result = builder.mul(
                        left,
                        right,
                        name="multmp"
                    )

            else:
                if not re.fullmatch(
                    r"[A-Za-z_][A-Za-z0-9_]*|-?\d+",
                    expression
                ):
                    compilation_error(
                        line_number,
                        "invalid expression"
                    )

                result = get_value(
                    expression,
                    line_number
                )

            builder.store(
                result,
                symbols[target]
            )

            continue

        # exit y
        exit_match = re.fullmatch(
            r"exit\s+([A-Za-z_][A-Za-z0-9_]*)",
            line
        )

        if exit_match:
            name = exit_match.group(1)

            if name not in symbols:
                compilation_error(
                    line_number,
                    f"undeclared variable '{name}'"
                )

            value = builder.load(
                symbols[name],
                name=f"load_{name}_exit"
            )

            fmt_ptr = builder.bitcast(
                fmt,
                ir.PointerType(I8)
            )

            builder.call(
                printf,
                [fmt_ptr, value]
            )

            builder.ret(
                ir.Constant(I32, 0)
            )

            found_exit = True

            if line_number != len(lines):
                for remaining in lines[line_number:]:
                    if remaining.strip():
                        compilation_error(
                            line_number + 1,
                            "exit must be the last statement"
                        )

            break

        compilation_error(
            line_number,
            "cannot parse line"
        )


    if not found_exit:
        compilation_error(
            len(lines),
            "no exit statement"
        )


    with open(output_path, "w") as f:
        f.write(str(module))


if __name__ == "__main__":
    main()
