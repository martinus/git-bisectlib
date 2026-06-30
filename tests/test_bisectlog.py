"""Tests for bisectlog against a real, freshly-built git repo + bisect session."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bisectlog  # noqa: E402


def run(cwd, *args, env=None, check=True):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=e)
    if check and p.returncode != 0:
        raise AssertionError(f"{args} failed: {p.stderr}\n{p.stdout}")
    return p


def make_repo(n=16, bug_at=11):
    """Build a linear repo of n commits; `bug_at` introduces the regression."""
    d = tempfile.mkdtemp(prefix="bisectlog-test-")
    run(d, "git", "init", "-q")
    run(d, "git", "config", "user.email", "t@t.t")
    run(d, "git", "config", "user.name", "Tester")
    shas = []
    for i in range(1, n + 1):
        content = "BUG\n" if i >= bug_at else "ok\n"
        Path(d, "code.txt").write_text(content)
        Path(d, f"f{i}.txt").write_text(str(i))
        run(d, "git", "add", "-A")
        # space commits a day apart so durations are meaningful
        date = f"2026-01-{i:02d}T12:00:00"
        run(d, "git", "commit", "-q", "-m", f"commit {i}",
            env={"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})
        shas.append(run(d, "git", "rev-parse", "HEAD").stdout.strip())
    return d, shas


class TestBisectlog(unittest.TestCase):
    def test_full_run_finds_first_bad(self):
        d, shas = make_repo(n=16, bug_at=11)
        bad, good = shas[-1], shas[0]
        bug_sha = shas[10]  # commit 11, 0-indexed

        # a `git bisect run` test script: exit 1 (bad) if BUG present, else 0 (good)
        script = Path(d, "t.sh")
        script.write_text("#!/bin/sh\ngrep -q BUG code.txt && exit 1\nexit 0\n")
        script.chmod(0o755)

        run(d, "git", "bisect", "start", bad, good)
        run(d, "git", "bisect", "run", "./t.sh")

        rep = bisectlog.build_report(d)
        self.assertIsNotNone(rep)
        self.assertEqual(rep.first_bad, bug_sha)
        self.assertEqual(rep.orig_bad, bad)
        self.assertIn(good, rep.orig_goods)
        # markdown + html render without error and mention the culprit
        md = bisectlog.render_markdown(rep)
        self.assertIn("First bad commit", md)
        self.assertIn(bug_sha[:9], md)
        html = bisectlog.render_html(rep)
        self.assertIn("firstbad", html)
        run(d, "git", "bisect", "reset")

    def test_midbisect_rows_and_bounds(self):
        d, shas = make_repo(n=16, bug_at=11)
        bad, good = shas[-1], shas[0]
        run(d, "git", "bisect", "start", bad, good)

        # one manual step: mark whatever git checked out
        head1 = run(d, "git", "rev-parse", "HEAD").stdout.strip()
        # decide truthfully: bad if it has the bug
        has_bug = "BUG" in Path(d, "code.txt").read_text()
        run(d, "git", "bisect", "bad" if has_bug else "good")

        rep = bisectlog.build_report(d)
        self.assertIsNotNone(rep)
        self.assertGreaterEqual(len(rep.rows), 1)
        # first row's midpoint is the first commit git checked out
        first = rep.rows[0]
        self.assertEqual(first.midpoint, head1)
        self.assertEqual(first.status, "bad" if has_bug else "good")
        # there should be an in-flight todo row for the new HEAD
        self.assertTrue(rep.in_progress)
        self.assertEqual(rep.rows[-1].status, "todo")
        # range metrics populated
        self.assertGreater(first.n_commits, 0)
        self.assertGreater(first.span_seconds, 0)
        run(d, "git", "bisect", "reset")

    def test_no_bisect_returns_none(self):
        d, _ = make_repo(n=4, bug_at=3)
        self.assertIsNone(bisectlog.build_report(d))

    def test_render_from_saved_log(self):
        d, shas = make_repo(n=8, bug_at=5)
        run(d, "git", "bisect", "start", shas[-1], shas[0])
        run(d, "git", "bisect", "good" if "BUG" not in Path(d, "code.txt").read_text()
            else "bad")
        log = bisectlog.bisect_log(d)
        rep = bisectlog.build_report(d, log_text=log)
        self.assertIsNotNone(rep)
        run(d, "git", "bisect", "reset")

    def test_fmt_duration(self):
        self.assertEqual(bisectlog.fmt_duration(0), "0m")
        self.assertEqual(bisectlog.fmt_duration(90), "1m")
        self.assertEqual(bisectlog.fmt_duration(3700), "1h 1m")
        self.assertEqual(bisectlog.fmt_duration(90000), "1d 1h 0m")


if __name__ == "__main__":
    unittest.main(verbosity=2)
