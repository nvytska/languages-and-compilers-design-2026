import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
COMPILER = ROOT / "compiler.py"


def main():
    runner = shutil.which("lli") or shutil.which("clang")
    if runner is None:
        print("Install lli or clang to execute the valid tests.", file=sys.stderr)
        return 1

    passed = 0
    failed = 0
    for folder in ("ok", "err"):
        for source in sorted((ROOT / "tests" / folder).glob("*.txt")):
            label = source.relative_to(ROOT)
            expected_file = source.with_suffix(".expected")
            if not expected_file.exists():
                print(f"MISSING EXPECTED: {label}")
                failed += 1
                continue
            expected = expected_file.read_text()
            input_file = source.with_suffix(".in")
            with tempfile.TemporaryDirectory(prefix="practice7_test_") as directory:
                output_file = Path(directory) / "output.ll"
                result = subprocess.run(
                    [sys.executable, str(COMPILER), str(source), str(output_file)],
                    capture_output=True, text=True,
                )
                actual = result.stderr
                if folder == "err":
                    success = result.returncode != 0 and actual == expected
                else:
                    success = False
                    if result.returncode == 0:
                        if Path(runner).name == "lli":
                            command = [runner, str(output_file)]
                        else:
                            executable = Path(directory) / "program"
                            link = subprocess.run(
                                [runner, str(output_file), "-o", str(executable)],
                                capture_output=True, text=True,
                            )
                            command = [str(executable)] if link.returncode == 0 else None
                            actual = link.stderr
                        if command is not None:
                            stdin = input_file.read_bytes() if input_file.exists() else b""
                            execution = subprocess.run(command, input=stdin, capture_output=True)
                            actual = (
                                execution.stdout.decode("utf-8", errors="replace")
                                if execution.returncode == 0
                                else execution.stderr.decode("utf-8", errors="replace")
                            )
                            success = execution.returncode == 0 and actual == expected
                if success:
                    print(f"PASS {label}")
                    passed += 1
                else:
                    print(f"FAIL {label}")
                    print(f"  Expected: {expected!r}")
                    print(f"  Actual:   {actual!r}")
                    failed += 1
    print(f"\nPassed: {passed}\nFailed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
