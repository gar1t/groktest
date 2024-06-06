import os
import re
import subprocess

__all__ = [
    "os",
    "re",
    "run",
]


def run(cmd: str):
    p = subprocess.run(
        cmd,
        shell=True,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": _groktest_home()},
    )
    print(p.stdout.decode())
    print(f"<{p.returncode}>")


def _groktest_home():
    return os.path.dirname(os.path.dirname(__file__))
