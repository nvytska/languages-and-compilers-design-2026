# Languages and Compilers Design 2026

Each practice uses a branch and a pull request into `main`. Practice 2 is on
`practice-2`. The compiler and tests stay at the repository root.

## Run

Python 3 is required. Install the compiler dependency:

```sh
python3 -m pip install -r requirements.txt
```

Print the Task 1 worked example (no llvmlite installation needed):

```sh
python3 compiler.py --tokens tests/lexer-example.txt
```

Run lexer tests:

```sh
python3 -m unittest discover -s tests -v
```

The compilation interface is:

```sh
python3 compiler.py input.txt output.ll
lli output.ll
```

Compilation also requires LLVM tools. The retained Practice 1 builder handles
the earlier syntax; Practice 2 token-based syntax integration is pending Task 2.
Lexer errors print `compilation error: line <line>:<column>: <message>` to stderr
and return a nonzero status.

## History and submission

The published initial commit contains only the original README. The next commit
recovers the Practice 1 baseline from the code retained in Practice 2 because the
original Practice 1 files were empty. History has not been rewritten.

Submit the repository link, the Practice 2 pull request link, and `ai_usage.txt`
after finishing both tasks. Request review from `vovaskochko`; merge only after
review. Task 1 is ready for review; Task 2 is not complete.
