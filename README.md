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

## Optimizations

`--remove-unused` enables an AST pass after semantic analysis and before LLVM
IR generation. It removes unused variable declarations, assignments to those
variables (including field assignments), and uncalled global functions. Uses
are counted per declaration, so shadowed names remain separate. Parameters,
fields, member functions, and lambda declarations are preserved. An unused
result of a pure call can be removed, including a pure method or lambda call.
An initializer or assignment value keeps its target if evaluating it can
have observable effects, including effects in call arguments or receivers.

Effect analysis marks functions that print, read input, mutate their receiver,
contain a loop, or participate in recursion. It propagates these effects from
callees to callers. The pass rebuilds the call graph after pruning, so a pure
function can be removed once its last call disappears.

The pass repeats counting and pruning until nothing is removed: dropping a
declaration or function may remove the last use of another one.
`--remove-unused --ast-checked` shows the optimized tree; `--ast` shows the
original parse tree. Without the flag compilation behaves as before.

Limitations: a self-feeding variable such as `k := k + 1` survives because its
right-hand side reads it. Mutually recursive global functions can survive even
when main calls neither: counting calls does not establish reachability.

Memory management: the compiler is written in Python and was tested with
CPython, which uses reference counting plus a cyclic garbage collector. A
removed subtree can be reclaimed when no strong references remain. AST nodes
have no general parent pointer. Semantic links such as `VarNode.decl` and
`CallNode.function` can retain declarations after they are unlinked; recursive
function links can form cycles. Strong parent pointers would add references
and create parent-child cycles, requiring cyclic collection after unlinking.
This concerns the compiler's memory, not heap deallocation in the compiled program.

Memory experiment: on `i32 x{10}\nexit 0`, a `weakref.ref` to the checked
declaration returned `None` after `remove_unused(program)` and `gc.collect()`:
`reference() is None` was **True**. No extra strong reference to the declaration
was retained. This experiment is also checked by
`PrunerTests.test_removed_declaration_is_collected` in `tests/test_pruner.py`.

Run regression tests in both modes with the virtual environment active:

```sh
python3 run_tests.py
REMOVE_UNUSED=1 python3 run_tests.py
```

The runner checks all programs in `tests/ok`, `tests/err`, and `tests/opt`.
Each of the twelve optimization examples has a `.txt` source, a reviewed `.astc`
optimized AST, and a `.expected` runtime output. Both runs check the optimized
AST snapshots; runtime compilation follows `REMOVE_UNUSED`. Success in both
modes verifies the same outputs and error messages with and without the pass.

## History and submission

The existing published initial commit contained only the README. The next commit
recovers the Practice 1 baseline from code retained in Practice 2 because the
original Practice 1 files were empty. Published history is preserved.

Repository: https://github.com/nvytska/languages-and-compilers-design-2026
Pull request: https://github.com/nvytska/languages-and-compilers-design-2026/pull/1

Submit these two links and `ai_usage.txt`. The repository is public. The required
review request to `vovaskochko` remains pending collaborator invitation approval
and acceptance. Merge after review.
