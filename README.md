# bisectlib + bisectlog

A Python toolkit for **automated `git bisect`**.

- **`bisectlog`** — a standalone, read-only CLI that renders any `git bisect`
  session as a nice **Markdown or HTML** report. Stdlib-only, single file.
- **`bisectlib`** — *(in progress)* a tiny recipe engine (`run` / `test` / `check`
  / `fixup` / `replace`) for writing `git bisect run` scripts that handle builds,
  flaky tests, benchmarks, per-range fixups, and the infrastructure-vs-result
  distinction.

See [`SPEC.md`](SPEC.md) for the full design.

## bisectlog (the renderer)

`bisectlog` derives its **entire** report from only:

1. `git bisect log` — which commits were evaluated, in what order, with what verdict;
2. per-commit information — git metadata, plus each commit's optional `eval.json`
   sidecar of recorded facts (commands, timings, flaky ratio, …) written by the engine.

No reflog, no `/proc`, no PID, no heuristic inference. If a fact wasn't logged or
recorded, it isn't shown.

### Usage

```sh
# during (or after) any bisect, from inside the repo:
bisectlog                      # Markdown to stdout
bisectlog --format html -o report.html
bisectlog --open               # render HTML and open in the browser
bisectlog --watch              # re-render as the bisect progresses
bisectlog -C /path/to/repo     # another repo/worktree
bisectlog --log saved.log      # render a saved `git bisect log` dump
bisectlog --details            # include per-commit command/timing detail (if recorded)
```

Installed as `git-bisectlog` it also works as **`git bisectlog`**.

### Example output

```
# Bisect report

**original range:** good `2801e9572` · bad `79cb050c2`

## 🎯 First bad commit: `5c9dcafb3` — commit 8: change subsystem 8

| bad | good | midpoint | range | status |
|-----|------|----------|-------|--------|
| `79cb050c2`<br>commit 12 | `2801e9572`<br>commit 1 | `cb5394973`<br>commit 6 | … · 11 commits | ✅ good |
| `79cb050c2`<br>commit 12 | `cb5394973`<br>commit 6 | `95345541b`<br>commit 9 | … ·  6 commits | ❌ bad |
| `95345541b`<br>commit 9  | `cb5394973`<br>commit 6 | `5c9dcafb3`<br>commit 8 | … ·  3 commits | ❌ bad |
| `5c9dcafb3`<br>commit 8  | `cb5394973`<br>commit 6 | `19d89b121`<br>commit 7 | … ·  2 commits | ✅ good |
```

Each row reads in causal order: the **input range** (`bad`/`good`) → the **midpoint**
git chose → the **status**. Watch the range funnel down as you scan top-to-bottom.

## Install

```sh
pip install -e .          # provides `bisectlog` and `git-bisectlog`
```

Requires Python 3.10+. `bisectlog` itself has **no dependencies** (only `git` on PATH).

## Development

```sh
python -m unittest discover -s tests -v
```

## License

MIT © Martin Leitner-Ankerl
