#!/usr/bin/env python3
"""Find the commit that made a test *start* being rarely flaky.

Some regressions only surface once in thousands of runs. `hammer` pounds on the
test to expose one. By default it runs on all cores for a minute; a single failure
makes the commit BAD, and it's GOOD only if the whole minute elapses with no
failure — the opposite of the flaky-tolerant `test(attempts=…)` quorum.

    git bisect start <BAD> <GOOD>
    git bisect run python examples/flaky_hunt.py
"""
from bisectlib import run, hammer

run("cmake -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo")
run("cmake --build build -j")

# Hammer the test on all cores for a minute; a single failure = bad.
hammer("./build/integration")
# tune the budget/threads if you like: hammer("./build/integration", for_seconds=120, parallel=8)
# reached the end -> no failure in a minute of hammering -> GOOD
