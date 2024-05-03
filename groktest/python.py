# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import *
from typing import IO
from types import CodeType
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

log = logging.getLogger(__name__)


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

    def init_for_tests(self, config: Optional[TestConfig] = None) -> None:
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
        env={**os.environ, "PYTHONNODEBUGRANGES": "1"},
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
    try:
        p.stdin.write("\n")
        p.stdin.flush()
    except OSError as e:
        if e.errno != 22:  # stream closed
            raise
    try:
        p.wait(timeout)
    except subprocess.TimeoutExpired:
        p.send_signal(_sigkill())


def _sigkill():
    # SIGKILL is not available on all platforms, fallback on SIGTERM
    return getattr(signal, "SIGKILL", signal.SIGTERM)


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
    resp_raw = input.readline()
    if not resp_raw:
        return TestResult(-9, "", "")
    try:
        resp = json.loads(resp_raw)
    except json.JSONDecodeError as e:
        return TestResult(-9, "", f"Invalid resp from runtime server: {resp_raw}")
    else:
        return TestResult(resp["code"], resp["output"], resp.get("short-error"))


def _update_vars(vars: Dict[str, Any], proc: Popen[str]):
    stdin, stdout = _proc_streams(proc)
    _write_vars_req(vars, stdin)
    _read_ack(stdout)


def _write_vars_req(vars: Dict[str, Any], out: IO[str]):
    req = json.dumps({"type": "vars", "vars": vars})
    _write_req(req, out)


def _parse_args():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def _init_logging():
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s: [%(name)s] %(message)s",
    )
    globals()["log"] = logging.getLogger("groktest.python")


def _main_loop():
    globals = {}
    while True:
        line = _readline()
        if not line:
            break
        req = _decode_request(line)
        if isinstance(req, TestReq):
            _handle_test_req(req, globals)
        elif isinstance(req, VarsReq):
            _handle_vars_req(req, globals)
        elif isinstance(req, InitReq):
            _handle_init_req(req, globals)
        else:
            assert False, req


def _readline():
    try:
        return sys.stdin.readline().rstrip()
    except OSError as e:
        if e.errno != 22:  # stream closed
            raise
        return ""


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


def _handle_test_req(test: TestReq, globals: Dict[str, Any]):
    _log_test(test)
    with _StdOutCapture(test.options) as out:
        try:
            _exec_test(test, globals)
        except:
            exc_info = sys.exc_info()
        else:
            exc_info = None
    _handle_test_result(out.getvalue(), exc_info, test)


def _log_test(test: TestReq):
    if test.options.get("debug") is False:
        return
    log.debug("Running Python test expr:")
    log.debug(textwrap.indent(test.expr, "  "))


def _handle_test_result(output: str, exc_info: Any, test: TestReq):
    _log_test_result(test, output, exc_info)
    _writeline(_encode_test_result(output, exc_info, test))


def _log_test_result(test: TestReq, output: str, exc_info: Any):
    if test.options.get("debug") is False:
        return
    log.debug("Test result:")
    log.debug(textwrap.indent(output, "  "))
    if exc_info and log.getEffectiveLevel() <= logging.DEBUG:
        log.debug("%s", _format_exc_info(exc_info))


class _StdOutCapture(io.StringIO):
    _stdout_save = None
    _stderr_save = None
    _log_handlers_save = None

    def __init__(self, options: TestOptions):
        super().__init__()
        self._capture_stderr = options.get("stderr")

    def __enter__(self):
        assert self._stdout_save is None
        assert self._stderr_save is None
        assert self._log_handlers_save is None
        self._stdout_save = sys.stdout
        sys.stdout = self
        if self._capture_stderr:
            self._stderr_save = sys.stderr
            sys.stderr = self
            self._log_handlers_save = _set_log_handlers(self)
        return self

    def __exit__(self, *exc: Any):
        assert self._stdout_save is not None
        sys.stdout = self._stdout_save
        self._stdout_save = None
        if self._stderr_save:
            assert self._stderr_save is not None
            sys.stderr = self._stderr_save
            self._stderr_save = None
            assert self._log_handlers_save is not None
            _restore_log_handlers(self._log_handlers_save)


def _set_log_handlers(stream: IO[str]):
    handlers: list[tuple[logging.Logger, list[logging.Handler]]] = []
    cur = log
    while cur:
        handlers.append((cur, cur.handlers))
        cur.handlers = [
            logging.StreamHandler(stream) if hasattr(h, "stream") else h
            for h in cur.handlers
        ]
        cur = cur.parent
    return handlers


def _restore_log_handlers(
    log_handlers: list[tuple[logging.Logger, list[logging.Handler]]]
):
    for logger, handlers in log_handlers:
        logger.handlers = handlers


def _exec_test(test: TestReq, globals: Dict[str, Any]):
    _apply_test_globals_effect(test, globals)
    code = _compile_test_expr(test)
    try:
        result = eval(code, globals)
    except AssertionError as e:
        _maybe_apply_code_vars(e, code, globals)
        raise
    else:
        _maybe_pretty_print_result(result, test.options)


def _maybe_apply_code_vars(e: AssertionError, code: CodeType, globals: Dict[str, Any]):
    if not e.args:
        e.args = (_code_vars(code, globals),)


def _code_vars(code: CodeType, globals: Dict[str, Any]):
    return {name: globals[name] for name in code.co_names if name in globals}


def _maybe_pretty_print_result(result: Any, options: TestOptions):
    if options.get("pprint"):
        pprint.pprint(result, width=72)
    elif options.get("json"):
        try:
            fmt = json.dumps(result, indent=2, sort_keys=True)
        except TypeError:
            pass
        else:
            print(fmt)


def _compile_test_expr(test: TestReq):
    """Returns compiled test expression.

    Tries to compile using 'eval' mode if test is configured for pretty
    print (`pprint` option is true), otherwise compiles using 'single'
    mode. 'single' mode prints evaluated results in the standard way (no
    pretty print format). If the expression can't be compiled for
    evaluation (i.e. we get a syntax error) we fall back on 'single'
    mode.
    """
    if not _wants_pretty_print(test.options):
        return _gen_compile_test_expr("single", test)

    # Wants pretty print - try 'eval' mode
    try:
        return _gen_compile_test_expr("eval", test)
    except SyntaxError:
        return _gen_compile_test_expr("single", test)


def _wants_pretty_print(options: TestOptions):
    return options.get("pprint") or options.get("json")


def _gen_compile_test_expr(mode: str, test: TestReq):
    return compile(
        _format_test_sourcecode(test),
        _test_filename(test),
        mode,
        dont_inherit=True,
    )


def _format_test_sourcecode(test: TestReq):
    """Returns test expression source code suitable for compile.

    Prepends empty lines to affect test source code line. In tracebacks
    we want to refer to the test source code file (filename) and the
    correct line number in that file. Empty lines is a convenient way to
    offset the line number accordingly.

    If the test expression is a comment, prepends "None " to the
    expression to coerce it to a parsable Python expression with the
    expected value of `None`.
    """
    expr = _coerce_comment(test.expr)
    if not test.filename or not test.line:
        return expr
    return "\n" * (test.line - 1) + expr


def _coerce_comment(expr: str):
    return f"None {expr}" if _is_comment(expr) else expr


def _is_comment(expr: str):
    return all(line.lstrip()[:1] == "#" for line in expr.split("\n"))


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


_FILE_SOURCECODE_PATTERN = re.compile(
    r"(?m)( +File \"(.+)\", line \d+, in .+\n)( +.+\n)?"
)


def _strip_error_detail(tb: str):
    parts = []
    charpos = 0
    for m in _FILE_SOURCECODE_PATTERN.finditer(tb):
        parts.append(tb[charpos : m.start()])
        charpos = m.end()
    parts.append(tb[charpos:])
    return "".join(parts)


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
    parts = []
    charpos = 0
    for m in _FILE_SOURCECODE_PATTERN.finditer(tb):
        parts.append(tb[charpos : m.start()])
        filename_line, filename, sourcecode = m.groups()
        charpos = m.end() if filename == __file__ else m.start()
    parts.append(tb[charpos:])
    return "".join(parts)


def _writeline(line: str):
    sys.stdout.write(line)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _handle_vars_req(vars: VarsReq, globals: Dict[str, Any]):
    _log_vars(vars)
    globals.update(vars.vars)
    _writeline(_encode_ack())


def _log_vars(vars: VarsReq):
    log.debug("Updating variables: %r", vars.vars)


def _handle_init_req(init: InitReq, globals: Dict[str, Any]):
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
    args = _parse_args()
    _init_logging()
    _main_loop()
