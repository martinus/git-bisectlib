"""Tests for the bisectlib recipe engine: exit-code contract, flaky logic,
clean-tree guarantee, and the eval.json sidecar."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sh(cwd, *args, env=None, check=True):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=e)
    if check and p.returncode != 0:
        raise AssertionError(f"{args} failed: {p.stderr}\n{p.stdout}")
    return p


def make_repo():
    d = tempfile.mkdtemp(prefix="bisectlib-eng-")
    sh(d, "git", "init", "-q")
    sh(d, "git", "config", "user.email", "t@t.t")
    sh(d, "git", "config", "user.name", "T")
    Path(d, "code.txt").write_text("original\n")
    sh(d, "git", "add", "-A")
    sh(d, "git", "commit", "-q", "-m", "c1")
    return d


def run_recipe(repo, body, cache=None):
    """Write `body` as a recipe and run it; return (exit_code, stderr, cache_dir)."""
    cache = cache or tempfile.mkdtemp(prefix="bl-cache-")
    recipe = Path(repo, "recipe.py")
    recipe.write_text("import sys\nsys.path.insert(0, %r)\n" % str(ROOT) + body)
    env = {"PYTHONPATH": str(ROOT), "XDG_CACHE_HOME": cache, "NO_COLOR": "1"}
    p = subprocess.run([sys.executable, "recipe.py"], cwd=repo,
                       capture_output=True, text=True, env={**os.environ, **env})
    return p.returncode, p.stderr, cache


class TestEngine(unittest.TestCase):
    def test_end_of_script_is_good(self):
        d = make_repo()
        code, _, _ = run_recipe(d, "import bisectlib as b\nb.run('true')\n")
        self.assertEqual(code, 0)

    def test_run_failure_aborts_by_default(self):
        d = make_repo()
        code, _, _ = run_recipe(d, "import bisectlib as b\nb.run('false')\n")
        self.assertEqual(code, 128)  # ABORT

    def test_run_failure_skip_on_error(self):
        d = make_repo()
        code, _, _ = run_recipe(
            d, "import bisectlib as b\nb.run('false', skip_on_error=True)\n")
        self.assertEqual(code, 125)  # SKIP

    def test_test_pass_is_good_fail_is_bad(self):
        d = make_repo()
        code, _, _ = run_recipe(d, "import bisectlib as b\nb.test('true')\n")
        self.assertEqual(code, 0)
        code, _, _ = run_recipe(d, "import bisectlib as b\nb.test('false')\n")
        self.assertEqual(code, 1)  # BAD

    def test_flaky_two_of_five(self):
        d = make_repo()
        # command passes its first 2 invocations, then fails -> 2/5
        cmd = r"c=$(cat n 2>/dev/null || echo 0); c=$((c+1)); echo $c>n; [ $c -le 2 ]"
        body = ("import bisectlib as b\n"
                f"b.test({cmd!r}, runs=5, need=2)\n")
        code, _, _ = run_recipe(d, body)
        self.assertEqual(code, 0)  # 2 passes meets need=2 -> good
        # need=3 would not be met
        d2 = make_repo()
        body2 = ("import bisectlib as b\n"
                 f"b.test({cmd!r}, runs=5, need=3)\n")
        code2, _, _ = run_recipe(d2, body2)
        self.assertEqual(code2, 1)  # bad

    def test_bad_when_pass_inverts(self):
        d = make_repo()
        # command always succeeds; bad_when='pass' means success == bad
        code, _, _ = run_recipe(
            d, "import bisectlib as b\nb.test('true', bad_when='pass')\n")
        self.assertEqual(code, 1)  # BAD

    def test_replace_reverts_tree(self):
        d = make_repo()
        body = ("import bisectlib as b\n"
                "b.replace('code.txt', 'original', 'patched')\n"
                "b.test('grep -q patched code.txt')\n")  # passes -> good
        code, _, _ = run_recipe(d, body)
        self.assertEqual(code, 0)
        # no tracked modifications must remain (untracked recipe.py is irrelevant
        # to git bisect's checkout); the edited file must be restored
        tracked = sh(d, "git", "status", "--porcelain",
                     "--untracked-files=no").stdout.strip()
        self.assertEqual(tracked, "")
        self.assertEqual(Path(d, "code.txt").read_text(), "original\n")

    def test_replace_missing_skips(self):
        d = make_repo()
        body = ("import bisectlib as b\n"
                "b.replace('code.txt', 'NOPE', 'x')\nb.test('true')\n")
        code, _, _ = run_recipe(d, body)
        self.assertEqual(code, 125)  # SKIP (pattern not found)

    def test_uncaught_exception_aborts(self):
        d = make_repo()
        code, _, _ = run_recipe(
            d, "import bisectlib as b\nraise RuntimeError('boom')\n")
        self.assertEqual(code, 128)  # ABORT, never 'bad'

    def test_check_does_not_exit(self):
        d = make_repo()
        body = ("import bisectlib as b\n"
                "r = b.check('echo hello')\n"
                "assert r.ok and 'hello' in r.out\n"
                "b.test('false')\n")  # we still reach test -> bad
        code, _, _ = run_recipe(d, body)
        self.assertEqual(code, 1)

    def test_sidecar_written(self):
        d = make_repo()
        body = ("import bisectlib as b\n"
                "b.run('true')\nb.test('true')\n")
        code, _, cache = run_recipe(d, body)
        self.assertEqual(code, 0)
        evals = list(Path(cache, "bisectlib").glob("*/*/eval.json"))
        self.assertTrue(evals, "expected an eval.json sidecar")
        data = json.loads(evals[0].read_text())
        self.assertEqual(data["outcome"], "good")
        self.assertEqual(len(data["steps"]), 2)
        self.assertEqual(data["steps"][0]["verb"], "run")
        self.assertEqual(data["steps"][1]["verb"], "test")


if __name__ == "__main__":
    unittest.main(verbosity=2)
