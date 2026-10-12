#!/usr/bin/env python3

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from llvmlite import binding as llvm


ROOT = Path(__file__).resolve().parent
COMPILER = ROOT / "compiler.py"


def run(command):
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
    )


def source_files(*folders):
    files = []
    for folder in folders:
        files.extend((ROOT / "tests" / folder).glob("*.txt"))
    return sorted(files)


def check_success(source, runner):
    expected = source.with_suffix(".expected").read_text()
    with tempfile.TemporaryDirectory() as folder:
        output = Path(folder) / "output.ll"
        compile_result = run(
            [sys.executable, str(COMPILER), str(source), str(output)]
        )
        if compile_result.returncode != 0:
            return False, compile_result.stderr.strip()
        if compile_result.stdout or compile_result.stderr:
            return False, "compiler produced unexpected output"

        try:
            llvm.parse_assembly(output.read_text()).verify()
        except RuntimeError as exception:
            return False, f"invalid LLVM IR: {exception}"

        if Path(runner).name == "lli":
            execute_result = run([runner, str(output)])
        else:
            executable = Path(folder) / "program"
            link_result = run([runner, str(output), "-o", str(executable)])
            if link_result.returncode != 0:
                return False, link_result.stderr.strip()
            execute_result = run([str(executable)])

        if execute_result.returncode != 0:
            return False, execute_result.stderr.strip()
        if execute_result.stderr:
            return False, execute_result.stderr.strip()
        if execute_result.stdout != expected:
            return (
                False,
                f"expected {expected.rstrip()!r}, got {execute_result.stdout.rstrip()!r}",
            )
        return True, ""


def check_error(source):
    expected = source.with_suffix(".expected").read_text()
    with tempfile.TemporaryDirectory() as folder:
        output = Path(folder) / "output.ll"
        result = run(
            [sys.executable, str(COMPILER), str(source), str(output)]
        )
        if result.returncode == 0:
            return False, "compiler unexpectedly succeeded"
        if result.stdout:
            return False, f"unexpected stdout: {result.stdout.rstrip()!r}"
        if result.stderr != expected:
            return (
                False,
                f"expected {expected.rstrip()!r}, got {result.stderr.rstrip()!r}",
            )
        if output.exists():
            return False, "failed compilation created an output file"
        return True, ""


def check_ast(expected):
    source = expected.with_suffix(".txt")
    result = run(
        [sys.executable, str(COMPILER), "--ast", str(source)]
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    if result.stderr:
        return False, result.stderr.strip()
    wanted = expected.read_text()
    if result.stdout != wanted:
        return (
            False,
            f"AST differs for {source.name}",
        )
    return True, ""


def main():
    runner = shutil.which("lli") or shutil.which("clang")
    if runner is None:
        print("Install lli or clang to run generated LLVM IR.", file=sys.stderr)
        return 1

    rows = []

    for source in source_files("valid", "ok"):
        passed, detail = check_success(source, runner)
        rows.append((passed, "run", source.relative_to(ROOT), detail))

    for source in source_files("invalid", "err"):
        passed, detail = check_error(source)
        rows.append((passed, "error", source.relative_to(ROOT), detail))

    ast_files = sorted([
        *(ROOT / "tests" / "valid").glob("*.ast"),
        *(ROOT / "tests" / "ok").glob("*.ast"),
    ])
    for expected in ast_files:
        passed, detail = check_ast(expected)
        rows.append((passed, "ast", expected.relative_to(ROOT), detail))

    print(f"{'STATUS':<6}  {'KIND':<5}  TEST")
    print(f"{'-' * 6}  {'-' * 5}  {'-' * 44}")
    for passed, kind, path, detail in rows:
        print(f"{'PASS' if passed else 'FAIL':<6}  {kind:<5}  {path}")
        if detail:
            print(f"                {detail}")

    passed_count = sum(passed for passed, _, _, _ in rows)
    print(f"\n{passed_count}/{len(rows)} checks passed")
    return 0 if passed_count == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
