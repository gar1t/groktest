# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import *

from subprocess import Popen

import io
import json
import logging
import os
import signal
import subprocess
import sys
import textwrap
import traceback

from .__init__ import Runtime
from .__init__ import Test
from .__init__ import TestConfig
from .__init__ import TestResult
from .__init__ import TestSpec

log = logging.getLogger("groktest.python")


class TestExpr:
    def __init__(
        self, expr: str, filename: Optional[str], compile_flags: Optional[int]
    ):
        self.expr = expr
        self.filename = filename
        self.compile_flags = compile_flags


class Init:
    def __init__(self, expr: str):
        self.expr = expr


class PythonRuntime(Runtime):
    config: Optional[TestSpec] = None
    _p: Optional[subprocess.Popen[str]] = None

    def init(self, config: Optional[TestConfig] = None):
        self._p = _open_proc()
        _init_runtime(config, self._p)

    def exec_test_expr(self, test: Test):
        return _exec_test_expr(test, _check_proc(self._p))

    def handle_bound_variables(self, bound_variables: Dict[str, Any]):
        # TODO Update proc with bound_variables - e.g. {"type": "vars":
        # "vars", bound_variables}
        pass

    def shutdown(self, timeout: int = 5):
        if self._p:
            _close_proc(self._p, timeout)
            self._p = None

    def is_available(self):
        return self._p is not None

    def __del__(self):
        self.shutdown(0)


def _open_proc():
    return subprocess.Popen(
        [sys.executable, "-m", "groktest.python", *_proc_args()],
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        text=True,
    )


def _proc_args() -> List[str]:
    if log.getEffectiveLevel() <= logging.DEBUG:
        return ["--debug"]
    return []


def _check_proc(p: Optional[Popen[str]]):
    if p is None:
        raise RuntimeError("runtime not initialized")
    return p


def _proc_streams(p: Popen[str]):
    assert p.stdin
    assert p.stdout
    return p.stdin, p.stdout


def _close_proc(p: Popen[str], timeout: int):
    assert p.stdin
    p.stdin.write("\n")
    p.stdin.flush()
    try:
        p.wait(timeout)
    except subprocess.TimeoutExpired:
        p.send_signal(signal.SIGKILL)


def _init_runtime(config: Optional[TestConfig], proc: Popen[str]):
    init_spec = config and config.get("python-init")
    if not init_spec:
        return
    if not isinstance(init_spec, (str, list)):
        log.warning(
            "python-init must be a string or list of strings "
            f"(got {type(init_spec).__name__})"
        )
        return
    if isinstance(init_spec, list):
        init_spec = "\n".join([str(line) for line in init_spec])
    stdin, stdout = _proc_streams(proc)
    _write_init_req(init_spec, stdin)
    _read_ack(stdout)


def _write_init_req(init: str, out: IO[str]):
    req = json.dumps({"type": "init", "expr": init})
    _write_req(req, out)


def _write_req(req: str, out: IO[str]):
    out.write(req)
    out.write("\n")
    out.flush()


def _exec_test_expr(test: Test, proc: Popen[str]):
    stdin, stdout = _proc_streams(proc)
    _write_test_req(test, stdin)
    return _read_test_result(stdout)


def _write_test_req(test: Test, out: IO[str]):
    req = json.dumps(
        {
            "type": "test",
            "expr": test.expr,
            "filename": test.filename,
            "compile-flags": 0,
        }
    )
    _write_req(req, out)


def _read_test_result(input: IO[str]):
    resp = json.loads(input.readline())
    return TestResult(resp["code"], resp["output"])


def _read_ack(input: IO[str]):
    resp = json.loads(input.readline())
    if resp != "ack":
        raise RuntimeError(resp)


def _main_loop():
    globals = {}
    while True:
        line = _readline()
        if not line:
            break
        req = _decode_request(line)
        if isinstance(req, TestExpr):
            _handle_test(req, globals)
        elif isinstance(req, Init):
            _handle_init(req, globals)
        else:
            assert False, req


def _readline():
    return sys.stdin.readline().rstrip()


def _decode_request(line: str):
    data = json.loads(line)
    if data["type"] == "test":
        return TestExpr(
            expr=data["expr"],
            filename=data.get("filename"),
            compile_flags=data.get("compfile-flags"),
        )
    elif data["type"] == "init":
        return Init(data["expr"])
    else:
        assert False, data


def _handle_test(test: TestExpr, globals: Dict[str, Any]):
    _log_test(test)
    with _StdOutCapture() as out:
        try:
            _exec_test(test, globals)
        except:
            error = sys.exc_info()
        else:
            error = None
    _handle_test_result(out.getvalue(), error)


def _log_test(test: TestExpr):
    log.debug("Running Python test expr:")
    log.debug(textwrap.indent(test.expr, "  "))


def _handle_test_result(output: str, exc_info: Any):
    _log_test_result(output, exc_info)
    _writeline(_encode_test_result(output, exc_info))


def _log_test_result(output: str, exc_info: Any):
    log.debug("Test result:")
    log.debug(textwrap.indent(output, "  "))
    if exc_info and log.getEffectiveLevel() <= logging.DEBUG:
        # Only format exc info if need be
        log.debug("%s", _format_exc_info(exc_info))


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


def _exec_test(test: TestExpr, globals: Dict[str, Any]):
    _apply_test_globals(test, globals)
    exec(
        compile(
            test.expr,
            test.filename or "<test>",
            "single",
            test.compile_flags or 0,
            dont_inherit=True,
        ),
        globals,
    )


def _apply_test_globals(test: TestExpr, globals: Dict[str, Any]):
    globals["__name__"] = (
        os.path.basename(test.filename) if test.filename else "__test__"
    )
    globals["__file__"] = test.filename or "__test__"


def _encode_test_result(output: str, exc_info: Any):
    return json.dumps(
        {
            "code": 0 if exc_info is None else 1,
            "output": output if exc_info is None else _format_exc_info(exc_info),
        }
    )


def _format_exc_info(exc_info: Any):
    out = io.StringIO()
    traceback.print_exception(*exc_info, file=out)
    return out.getvalue()


def _writeline(line: str):
    sys.stdout.write(line)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _handle_init(init: Init, globals: Dict[str, Any]):
    _log_init(init)
    try:
        exec(init.expr, globals)
    except Exception as e:
        log.exception("Error initializing Python runtime")
    _writeline(_encode_ack())


def _log_init(init: Init):
    log.debug("Initializing Python runtime")
    log.debug(textwrap.indent(init.expr, "  "))


def _encode_ack():
    return json.dumps("ack")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--debug", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s: [%(name)s] %(message)s",
    )

    globals()["log"] = logging.getLogger("groktest.python")

    _main_loop()
