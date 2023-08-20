# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import *

from subprocess import Popen

import io
import json
import signal
import subprocess
import sys

from .__init__ import Config
from .__init__ import Runtime
from .__init__ import Test
from .__init__ import TestResult


class TestExpr:
    def __init__(self, expr: str, filename: str, flags: int):
        self.expr = expr
        self.filename = filename
        self.flags = flags


class RuntimeInit:
    def __init__(self, expr: str):
        self.expr = expr


class PythonRuntime(Runtime):
    config: Optional[Config] = None
    _p: Optional[subprocess.Popen[str]] = None

    def init(self, config: Config):
        # TODO: config should have some sort of runtime init spec - e.g.
        # a dict of str -> str with keys as global names and vals as
        # import specs - suggested user config `{"runtime": {"name":
        # "...", "env": {...}}}` as an extention of the config
        # `{"runtime": "..."}` - this will work with Python and shell
        # and provides a generalized input to runtime init (this might
        # not be ideal UX as runtime is implied by type and associated
        # config - how then the specify extra globals without much
        # ceremony?)
        self.config = config
        self._p = _open_proc()

    def run_test(self, test: Test):
        p, stdin, stdout = _check_proc(self._p)
        _write_test_req(test, stdin)
        return _read_test_result(stdout)

    def handle_bound_variables(self, bound_variables: Dict[str, Any]):
        print(f"TODO: do something with bound variables {bound_variables}")

    def shutdown(self, timeout: int = 5):
        if self._p:
            _close_proc(self._p, timeout)
            self._p = None

    def is_available(self):
        return self._p is not None

    def __del__(self):
        self.shutdown(0)


def _check_proc(p: Optional[Popen[str]]):
    if p is None:
        raise RuntimeError("runtime not initialized")
    assert p.stdin
    assert p.stdout
    return p, p.stdin, p.stdout


def _open_proc():
    return subprocess.Popen(
        [sys.executable, "-m", "groktest.python"],
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        text=True,
    )


def _close_proc(p: Popen[str], timeout: int):
    assert p.stdin
    p.stdin.write("\n")
    p.stdin.flush()
    p.wait(timeout)
    if p.poll() is None:
        p.send_signal(signal.SIGKILL)


def _write_test_req(test: Test, out: IO[str]):
    req = json.dumps(
        {
            "type": "test",
            "expr": test.expr,
            "filename": test.source.filename,
            "flags": 0,  # TODO support for custom Python compile flags
        }
    )
    out.write(req)
    out.write("\n")
    out.flush()


def _read_test_result(input: IO[str]):
    resp = json.loads(input.readline())
    return TestResult(resp["code"], resp["output"])


def _main_loop():
    while True:
        line = _readline()
        if not line:
            break
        req = _decode_request(line)
        if isinstance(req, TestExpr):
            _handle_test(req)
        elif isinstance(req, RuntimeInit):
            _handle_runtime_init(req)
        else:
            assert False, req


def _readline():
    return sys.stdin.readline().rstrip()


def _decode_request(line: str):
    data = json.loads(line)
    # Proceed without type checking as errors are obvious
    if data["type"] == "test":
        return TestExpr(
            data["expr"],
            data.get("filename", "<unknown>"),
            data.get("flags", 0),
        )
    elif data["type"] == "init":
        return RuntimeInit(data["expr"])
    else:
        assert False, data


def _handle_test(test: TestExpr):
    with _StdOutCapture() as out:
        try:
            _exec_test(test)
        except:
            error = sys.exc_info()
        else:
            error = None
    _writeline(_encode_test_result(out.getvalue(), error))


class _StdOutCapture(io.StringIO):
    _real_stdout = None

    def __enter__(self):
        assert not self._real_stdout
        self._real_stdout = sys.stdout
        sys.stdout = self
        return self

    def __exit__(self, *exc: Any):
        assert self._real_stdout
        sys.stdout = self._real_stdout
        self._real_stdout = None


def _exec_test(test: TestExpr):
    # TODO: Globals needs to sync with runtime init + updates to bound
    # variables
    globals = {}
    exec(
        compile(
            test.expr,
            test.filename,
            "single",
            test.flags,
            dont_inherit=True,
        ),
        globals,
    )


def _encode_test_result(output: str, exc_info: Any):
    # TODO: how to encode current exc traceback?
    return json.dumps(
        {
            "code": 0 if exc_info is None else 1,
            "output": output,
        }
    )


def _writeline(line: str):
    sys.stdout.write(line)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _handle_runtime_init(init: RuntimeInit):
    print("TOOD: handle runtime init")


if __name__ == "__main__":
    _main_loop()
