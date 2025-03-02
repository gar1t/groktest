import os
import re
import subprocess

__all__ = [
    "os",
    "re",
    "run",
]


def run(cmd: str, env: dict[str, str] | None = None):
    env = {
        **os.environ,
        **(env or {}),
        "PYTHONPATH": _groktest_home(),
    }
    p = subprocess.run(
        cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, env=env
    )
    print(p.stdout.decode())
    print(f"<{p.returncode}>")


def _groktest_home():
    return os.path.dirname(os.path.dirname(__file__))
