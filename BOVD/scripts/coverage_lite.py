"""
Standard-library line-coverage runner (no 'coverage' package needed).

Usage:  python scripts/coverage_lite.py [pytest args]

Runs pytest under sys.monitoring (Python ≥ 3.12) and reports line coverage
for every module in astra/. Executable lines come from the compiled code
objects (co_lines); blocks whose first line carries "pragma: no cover" are
excluded, like coverage.py. This is an approximation of coverage.py's
statement coverage, good enough for the ≥ 80 % quality gate.
"""
from __future__ import annotations

import ast
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "astra"
sys.path.insert(0, str(ROOT))
hits: dict[str, set[int]] = {}


def executable(path: Path) -> set[int]:
    src = path.read_text(encoding="utf-8")
    code = compile(src, str(path), "exec")
    lines: set[int] = set()

    def walk(co: types.CodeType) -> None:
        for _, _, ln in co.co_lines():
            if ln:
                lines.add(ln)
        for c in co.co_consts:
            if isinstance(c, types.CodeType):
                walk(c)

    walk(code)
    src_lines = src.splitlines()
    excl: set[int] = set()
    for node in ast.walk(ast.parse(src)):
        ln = getattr(node, "lineno", None)
        if ln and "pragma: no cover" in src_lines[ln - 1]:
            excl.update(range(ln, (getattr(node, "end_lineno", ln) or ln) + 1))
        # docstrings are not statements
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) and isinstance(first.value.value, str):
                excl.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return lines - excl


def main() -> int:
    mon = sys.monitoring
    tid = mon.COVERAGE_ID
    mon.use_tool_id(tid, "coverage-lite")
    pkg = str(PKG)

    def on_line(code: types.CodeType, line: int) -> object:
        f = code.co_filename
        if f.startswith(pkg):
            hits.setdefault(f, set()).add(line)
            return None
        return mon.DISABLE

    mon.register_callback(tid, mon.events.LINE, on_line)
    mon.set_events(tid, mon.events.LINE)
    import pytest
    rc = pytest.main(["-q", *sys.argv[1:]])
    mon.set_events(tid, 0)
    tot_e = tot_h = 0
    rows = []
    for p in sorted(PKG.rglob("*.py")):
        ex = executable(p)
        h = hits.get(str(p), set()) & ex
        tot_e += len(ex)
        tot_h += len(h)
        rows.append((str(p.relative_to(ROOT)), len(ex), len(h), 100 * len(h) / len(ex) if ex else 100.0))
    print("\n{:<40} {:>6} {:>6} {:>7}".format("module", "lines", "hit", "cover"))
    for r in rows:
        print("{:<40} {:>6} {:>6} {:>6.1f}%".format(*r))
    print("{:<40} {:>6} {:>6} {:>6.1f}%".format("TOTAL", tot_e, tot_h, 100 * tot_h / tot_e))
    gate = [r for r in rows if r[0].startswith(("astra/engine", "astra/validation", "astra/features"))]
    ge = sum(r[1] for r in gate)
    gh = sum(r[2] for r in gate)
    print(f"\nQuality gate (engine + validation + features): {100 * gh / ge:.1f}% (target ≥ 80%)")
    return int(rc)


if __name__ == "__main__":
    sys.exit(main())
