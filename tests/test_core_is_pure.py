"""Invariant: core/ is pure math and must not depend on the web layer."""
import pathlib

FORBIDDEN = ("fastapi", "starlette", "uvicorn", "pydantic")


def test_core_has_no_web_imports():
    offenders = []
    for path in pathlib.Path("core").rglob("*.py"):
        for line in path.read_text().splitlines():
            s = line.strip()
            if s.startswith(("import ", "from ")) and any(f in s for f in FORBIDDEN):
                offenders.append(f"{path}: {s}")
    assert offenders == [], offenders
