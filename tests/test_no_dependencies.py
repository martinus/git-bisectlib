"""Guard the project's zero-dependency guarantee.

`bisectlib` must import nothing outside the Python standard library. The tool
runs on developers' and CI machines against arbitrary checkouts, so keeping the
dependency set empty minimizes the supply-chain attack surface — there is no
transitive tree to audit or to be compromised upstream (see SPEC.md §8
"Packaging"). This test statically parses every module in the package and fails
if any import resolves to a non-stdlib, third-party package."""
import ast
import sys
import unittest
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "bisectlib"
PACKAGE_NAME = "bisectlib"

# Top-level module names that are allowed. Everything in the standard library,
# plus __future__ (a pseudo-module) and the package's own name for absolute
# self-imports like `from bisectlib import _report`.
ALLOWED = set(sys.stdlib_module_names) | {"__future__", PACKAGE_NAME}


def _imported_top_level_modules(tree):
    """Every top-level module name imported anywhere in an AST.

    Walks the whole tree, so lazy imports inside functions are covered too.
    Relative imports (`from . import x`) are internal and yield nothing.
    """
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import -> internal, skip
                continue
            if node.module:
                names.add(node.module.split(".")[0])
    return names


class TestNoExternalDependencies(unittest.TestCase):
    def test_package_imports_only_stdlib(self):
        offenders = {}  # module name -> sorted list of files that import it
        py_files = sorted(PACKAGE_DIR.rglob("*.py"))
        self.assertTrue(py_files, f"no python files found under {PACKAGE_DIR}")
        for path in py_files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for mod in _imported_top_level_modules(tree):
                if mod not in ALLOWED:
                    offenders.setdefault(mod, []).append(path.name)
        self.assertEqual(
            offenders,
            {},
            "bisectlib must stay dependency-free (stdlib only). "
            f"Found third-party imports: {offenders}",
        )


if __name__ == "__main__":
    unittest.main()
