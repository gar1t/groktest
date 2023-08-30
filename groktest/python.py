# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import *

from subprocess import Popen

import io
import json
import logging
import os
import pprint
import re
import signal
import subprocess
import sys
import textwrap
import traceback
from typing import Optional

from groktest import TestConfig

from .__init__ import Runtime
from .__init__ import Test
from .__init__ import TestConfig
from .__init__ import TestMatch
from .__init__ import TestOptions
from .__init__ import TestResult

log = logging.getLogger("groktest.python")


class InitReq:
    def __init__(self, expr: str):
        self.expr = expr


class TestReq:
    def __init__(
        self,
        expr: str,
        filename: Optional[str],
        line: Optional[int],
        options: Optional[TestOptions],
    ):
        self.expr = expr
        self.filename = filename
        self.line = line
        self.options = options or {}


class VarsReq:
    def __init__(self, vars: Dict[str, Any]):
        self.vars = vars


class PythonRuntime(Runtime):
    _p: Optional[subprocess.Popen[str]] = None

    def start(self, config: Optional[TestConfig] = None):
        self._p = _open_proc()

    def init_for_tests(self, config: TestConfig | None = None) -> None:
        if config:
            _init_for_tests(config, _check_proc(self._p))

    def exec_test_expr(self, test: Test, options: TestOptions):
        return _exec_test_expr(test, options, _check_proc(self._p))

    def handle_test_match(self, match: TestMatch):
        if match.match and match.vars:
            _update_vars(match.vars, _check_proc(self._p))

    def stop(self, timeout: int = 5):
        if self._p:
            _close_proc(self._p, timeout)
            self._p = None

    def is_available(self):
        return self._p is not None

    def __del__(self):
        self.stop(0)


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


def _init_for_tests(config: TestConfig, proc: Popen[str]):
    init_expr = _init_expr(config)
    if not init_expr:
        return
    stdin, stdout = _proc_streams(proc)
    _write_init_req(init_expr, stdin)
    _read_ack(stdout)


def _init_expr(config: TestConfig):
    try:
        expr = config["python"]["init"]
    except KeyError:
        return None
    else:
        if not isinstance(expr, (str, list)):
            log.warning(
                "python init must be a string or list of strings "
                f"(got {type(expr).__name__})"
            )
            return None
        if isinstance(expr, list):
            expr = "\n".join([str(line) for line in expr])
        return expr


def _write_init_req(init: str, out: IO[str]):
    req = json.dumps({"type": "init", "expr": init})
    _write_req(req, out)


def _write_req(req: str, out: IO[str]):
    out.write(req)
    out.write("\n")
    out.flush()


def _read_ack(input: IO[str]):
    resp = json.loads(input.readline())
    if resp != "ack":
        raise RuntimeError(resp)


def _exec_test_expr(test: Test, options: TestOptions, proc: Popen[str]):
    stdin, stdout = _proc_streams(proc)
    _write_test_exec_req(test, options, stdin)
    return _read_test_result(stdout)


def _write_test_exec_req(test: Test, options: TestOptions, out: IO[str]):
    req = json.dumps(
        {
            "type": "test",
            "expr": test.expr,
            "filename": test.filename,
            "line": test.line,
            "options": options,
        }
    )
    _write_req(req, out)


def _read_test_result(input: IO[str]):
    resp = json.loads(input.readline())
    return TestResult(resp["code"], resp["output"], resp.get("short-error"))


def _update_vars(vars: Dict[str, Any], proc: Popen[str]):
    stdin, stdout = _proc_streams(proc)
    _write_vars_req(vars, stdin)
    _read_ack(stdout)


def _write_vars_req(vars: Dict[str, Any], out: IO[str]):
    req = json.dumps({"type": "vars", "vars": vars})
    _write_req(req, out)


def _main_loop():
    globals = {}
    while True:
        line = _readline()
        if not line:
            break
        req = _decode_request(line)
        if isinstance(req, TestReq):
            _handle_test(req, globals)
        elif isinstance(req, VarsReq):
            _handle_vars(req, globals)
        elif isinstance(req, InitReq):
            _handle_init(req, globals)
        else:
            assert False, req


def _readline():
    return sys.stdin.readline().rstrip()


def _decode_request(line: str):
    data = json.loads(line)
    if data["type"] == "test":
        return TestReq(
            expr=data["expr"],
            filename=data.get("filename"),
            line=data.get("line"),
            options=data.get("options"),
        )
    elif data["type"] == "vars":
        return VarsReq(data["vars"])
    elif data["type"] == "init":
        return InitReq(data["expr"])
    else:
        assert False, data


def _handle_test(test: TestReq, globals: Dict[str, Any]):
    _log_test(test)
    with _StdOutCapture() as out:
        try:
            _exec_test(test, globals)
        except:
            exc_info = sys.exc_info()
        else:
            exc_info = None
    _handle_test_result(out.getvalue(), exc_info, test)


def _log_test(test: TestReq):
    log.debug("Running Python test expr:")
    log.debug(textwrap.indent(test.expr, "  "))


def _handle_test_result(output: str, exc_info: Any, test: TestReq):
    _log_test_result(output, exc_info)
    _writeline(_encode_test_result(output, exc_info, test))


def _log_test_result(output: str, exc_info: Any):
    log.debug("Test result:")
    log.debug(textwrap.indent(output, "  "))
    if exc_info and log.getEffectiveLevel() <= logging.DEBUG:
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


def _exec_test(test: TestReq, globals: Dict[str, Any]):
    _apply_test_globals_effect(test, globals)
    code = _compile_test_expr(test)
    result = eval(code, globals)
    _maybe_pretty_print_result(result, test.options)


def _maybe_pretty_print_result(result: Any, options: TestOptions):
    if result is None or not options.get("pprint"):
        return
    pprint.pprint(result, width=72)


def _compile_test_expr(test: TestReq):
    """Returns compiled test expression.

    Tries to compile using 'eval' mode if test is configured for pretty
    print (`pprint` option is true), otherwise compiles using 'single'
    mode. 'single' mode prints evaluated results in the standard way (no
    pretty print format). If the expression can't be compiled for
    evaluation (i.e. we get a syntax error) we fall back on 'single'
    mode.
    """
    if not test.options.get("pprint"):
        return _gen_compile_test_expr("single", test)

    # Test wants pretty print - try 'eval' mode
    try:
        return _gen_compile_test_expr("eval", test)
    except SyntaxError:
        return _gen_compile_test_expr("single", test)


def _gen_compile_test_expr(mode: str, test: TestReq):
    return compile(
        _format_test_sourcecode(test),
        _test_filename(test),
        mode,
        dont_inherit=True,
    )


def _format_test_sourcecode(test: TestReq):
    """Returns test expression source code suitable for compile.

    Preppends empty lines to affect test source code line. In tracebacks
    we want to refer to the test source code file (filename) and the
    correct line number in that file. Empty lines is a convenient way to
    offset the line number accordingly.
    """
    if not test.filename or not test.line:
        return test.expr
    return "\n" * (test.line - 1) + test.expr


def _test_filename(test: TestReq):
    return test.filename if test.filename else "<test>"


def _apply_test_globals_effect(test: TestReq, globals: Dict[str, Any]):
    globals["__name__"] = (
        os.path.basename(test.filename) if test.filename else "__test__"
    )
    globals["__file__"] = test.filename or "__test__"


def _encode_test_result(output: str, exc_info: Any, test: TestReq):
    if exc_info:
        output, short_error = _format_error_output(exc_info, test)
        code = 1
    else:
        short_error = None
        code = 0
    return json.dumps({"code": code, "output": output, "short-error": short_error})


def _format_error_output(exc_info: Any, test: Optional[TestReq] = None):
    """Returns a tuple of full error and short error.

    Full error is a formatted traceback with two adjustments:

      - Internal calls (i.e. calls from this module) are removed
      - Doc test prompts (PS1 and PS2) are stripped from error source
        code originating from the test file

    Short error is contains only the traceback header and the exception
    name - call stack details are removed.
    """
    formatted = _format_exc_info(exc_info)
    full_error = _format_full_error(formatted, test)
    short_error = _strip_error_detail(formatted)
    return full_error, short_error


def _format_exc_info(exc_info: Any):
    out = io.StringIO()
    traceback.print_exception(*exc_info, file=out)
    return out.getvalue()


def _format_full_error(tb: str, test: Optional[TestReq]):
    return _strip_doctest_prompts(_strip_internal_calls(tb), test)


def _strip_error_detail(tb: str):
    parts = []
    charpos = 0
    for m in _FILE_SOURCECODE_PATTERN.finditer(tb):
        parts.append(tb[charpos : m.start()])
        charpos = m.end()
    parts.append(tb[charpos:])
    return "".join(parts)


_FILE_SOURCECODE_PATTERN = re.compile(
    r"(?m)( +File \"(.+)\", line \d+, in .+\n)( +.+\n)?"
)


def _strip_doctest_prompts(tb: str, test: Optional[TestReq]):
    if not test or not test.filename:
        return tb
    parts = []
    charpos = 0
    for m in _FILE_SOURCECODE_PATTERN.finditer(tb):
        parts.append(tb[charpos : m.start()])
        filename_line, filename, sourcecode = m.groups()
        parts.append(filename_line)
        if sourcecode is not None:
            parts.append(
                _strip_prompt(sourcecode) if filename == test.filename else sourcecode
            )
        charpos = m.end()
    parts.append(tb[charpos:])
    return "".join(parts)


def _strip_prompt(s: str):
    m = re.match(r"( +)([^ ]+ )(.*\n)", s)
    if not m:
        return s
    return m.group(1) + m.group(3)


def _strip_internal_calls(tb: str):
    lines = tb.split("\n")
    header = lines[0]
    stripped_lines = lines[5:]
    assert stripped_lines and stripped_lines[0].endswith(" <module>"), lines
    return "\n".join([header] + stripped_lines)


def _writeline(line: str):
    sys.stdout.write(line)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _handle_vars(vars: VarsReq, globals: Dict[str, Any]):
    _log_vars(vars)
    globals.update(vars.vars)
    _writeline(_encode_ack())


def _log_vars(vars: VarsReq):
    log.debug("Updating variables: %r", vars.vars)


def _handle_init(init: InitReq, globals: Dict[str, Any]):
    _log_init(init)
    globals.clear()
    try:
        exec(init.expr, globals)
    except Exception as e:
        log.exception("Error initializing Python runtime")
    _writeline(_encode_ack())


def _log_init(init: InitReq):
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
