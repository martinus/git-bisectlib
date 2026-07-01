#!/usr/bin/env python3
"""A metric bisect: find where a numeric budget was crossed.

Here: the commit where the built binary first exceeded 5 MiB. Measure with
check() and decide with the bad()/good() verdict primitives — the comparison
stays in Python, no shelling out to `test`. Any measurable number works the
same way — startup time, generated-code line count, a memory high-water mark.

    git bisect start <BAD> <GOOD>
    git bisect run python examples/metric_binary_size.py
"""
from bisectlib import run, check, bad

run("make -j")
size = int(check("stat -c%s build/app").out or 0)   # measure (never exits)
print(f"binary is {size / 1024 / 1024:.2f} MiB")

if size > 5 * 1024 * 1024:
    bad(f"{size} bytes exceeds the 5 MiB budget")   # this commit is bad
# otherwise fall through to the end -> good
