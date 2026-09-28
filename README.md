# Languages and Compilers Design 2026

The compiler and tests live at the repository root. Practice 3 adds a grammar,
recursive-descent parser, abstract syntax tree, and tree-based code generation.

## Setup

Use Python 3 and install llvmlite in a local virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Install LLVM tools to use `lli` or `llc`. The tests can also compile and run the
LLVM IR using `clang` if `lli` is unavailable.

## Compile and run

```sh
python3 compiler.py tests/valid/worked-example.txt output.ll
lli output.ll
```

Expected: `Program exit with result 70`.

Alternatively, build a binary:

```sh
llc -filetype=obj -relocation-model=pic output.ll -o output.o
clang -fPIE output.o -o program
./program
```

With clang alone:

```sh
clang output.ll -o program
./program
```

Print the lexer worked example (also works without installing llvmlite):

```sh
python3 compiler.py --tokens tests/lexer-example.txt
```

Print an AST without generating LLVM IR:

```sh
python3 compiler.py --ast tests/valid/worked-example.txt
python3 compiler.py --ast tests/valid/precedence.txt
```

The language grammar is in `grammar.ebnf`. The Task 4 example is
`tests/valid/task4-example.txt` and prints `Program exit with result 120`.

## Language

- `i32 x{5}` declares a constant; `i32 mut y{10}` declares a mutable variable.
- Initialisers and assignment values are chains of constants and variables
  joined by `+`, `-`, and `*`. Multiplication binds tighter; operators of equal
  precedence associate left to right. Numbers are unsigned decimal tokens
  in the range 0 through 2147483647; subtraction can produce negative results.
- `y := x + 3` assigns only to a mutable variable.
- `exit y` or `exit 42` prints the value and ends the program.
- One statement per line; spaces, tabs, and blank lines are allowed.

The lexer scans ASCII bytes through explicit states. The parser consumes only
its tokens and builds an AST before code generation. All LLVM IR is generated
through `llvmlite.ir` builder calls.
Errors print one line to stderr with a 1-based byte line and column and return a
nonzero status. Failed compilation does not create or overwrite the output file.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Each program in `tests/valid/` and `tests/invalid/` has a neighbouring
`.expected` file. The tests verify LLVM IR, run valid programs through lli or
clang, compare exact error messages and AST dumps, and check output-file
preservation. Lexer tests check token kinds and positions.

## History and submission

The existing published initial commit contained only the README. The next commit
recovers the Practice 1 baseline from code retained in Practice 2 because the
original Practice 1 files were empty. Published history is preserved.

Repository: https://github.com/nvytska/languages-and-compilers-design-2026
Pull request: https://github.com/nvytska/languages-and-compilers-design-2026/pull/1

Submit these two links and `ai_usage.txt`. The repository is public. The required
review request to `vovaskochko` remains pending collaborator invitation approval
and acceptance. Merge after review.
