# Languages and Compilers Design 2026

## Practice 1 baseline

Install Python 3, llvmlite, and LLVM tools. Install the Python dependency with:

```sh
python3 -m pip install llvmlite
```

Compile and run:

```sh
python3 compiler.py input.txt output.ll
lli output.ll
```

The original `practice-1/compiler.py` was empty. This baseline was recovered
from the earlier compiler code retained in `practice-2/compiler.py`, with the
missing LLVM integer type definitions restored. The published README-only
initial commit is preserved.
