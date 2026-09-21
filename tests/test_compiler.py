import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llvmlite import binding as llvm


class CompilerTests(unittest.TestCase):
    def compile(self, source, output):
        return subprocess.run([sys.executable, str(ROOT / 'compiler.py'), str(source), str(output)],
                              capture_output=True, text=True)

    def test_ast_dumps(self):
        for source in sorted((ROOT / 'tests/valid').glob('*.ast')):
            with self.subTest(program=source.stem):
                result = subprocess.run(
                    [sys.executable, str(ROOT / 'compiler.py'), '--ast',
                     str(source.with_suffix('.txt'))],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, source.read_text())

    def test_valid_programs_compile_verify_and_run(self):
        runner = shutil.which('lli') or shutil.which('clang')
        self.assertIsNotNone(runner, 'Install lli or clang to run the valid programs')
        for source in sorted((ROOT / 'tests/valid').glob('*.txt')):
            with self.subTest(program=source.stem), tempfile.TemporaryDirectory() as folder:
                output = Path(folder) / 'output.ll'
                result = self.compile(source, output)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(result.stdout, '')
                llvm.parse_assembly(output.read_text()).verify()
                if Path(runner).name == 'lli':
                    command = [runner, str(output)]
                else:
                    executable = Path(folder) / 'program'
                    link = subprocess.run([runner, str(output), '-o', str(executable)], capture_output=True, text=True)
                    self.assertEqual(link.returncode, 0, link.stderr)
                    command = [str(executable)]
                run = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, source.with_suffix('.expected').read_text())
                self.assertEqual(run.stderr, '')

    def test_invalid_programs_and_output_preservation(self):
        for source in sorted((ROOT / 'tests/invalid').glob('*.txt')):
            with self.subTest(program=source.stem), tempfile.TemporaryDirectory() as folder:
                output = Path(folder) / 'output.ll'
                for existing in (False, True):
                    if existing:
                        output.write_text('existing output\n')
                    result = self.compile(source, output)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, '')
                    self.assertEqual(result.stderr, source.with_suffix('.expected').read_text())
                    if existing:
                        self.assertEqual(output.read_text(), 'existing output\n')
                    else:
                        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
