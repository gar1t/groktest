# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import *

import configparser
import importlib
import json
import logging
import re

from . import _vendor_parse as parselib

__all__ = [
    "Config",
    "CONFIG",
    "DEFAULT_CONFIG",
    "init_runner_state",
    "init_runtime",
    "match_test_output",
    "MatchTypes",
    "parse_tests",
    "PYTHON_CONFIG",
    "RunnerState",
    "Runtime",
    "RUNTIME",
    "test_file",
    "Test",
    "TestMatch",
    "TestResult",
]

log = logging.getLogger("groktest")


class Error(Exception):
    pass


class TestTypeNotSupported(Error):
    pass


class RuntimeNotSupported(Error):
    pass


MatchTypes = Dict[str, str]


class Config:
    def __init__(
        self,
        name: str,
        runtime: str,
        ps1: str,
        ps2: str,
        test_pattern: str,
        blankline: str,
        match_types: MatchTypes,
    ):
        self.name = name
        self.runtime = runtime
        self.ps1 = ps1
        self.ps2 = ps2
        self.test_pattern = re.compile(
            test_pattern.format(
                ps1=re.escape(ps1),
                ps2=re.escape(ps2),
            ),
            re.MULTILINE | re.VERBOSE,
        )
        self.blankline = blankline
        self.match_types = match_types

    def __str__(self):
        return f"<groktest.Config '{self.name}'>"


TestOptions = Dict[str, Any]


class Test:
    def __init__(
        self, expr: str, expected: str, filename: str, line: int, options: TestOptions
    ):
        self.expr = expr
        self.expected = expected
        self.filename = filename
        self.line = line


class TestResult:
    def __init__(self, code: int, output: str):
        self.code = code
        self.output = output


class TestMatch:
    def __init__(self, bound_variables: Dict[str, Any]):
        self.bound_variables = bound_variables


class Runtime:
    def exec_test_expr(self, test: Test) -> TestResult:
        raise NotImplementedError()

    def handle_bound_variables(self, bound_variables: Dict[str, Any]) -> None:
        raise NotImplementedError()

    def shutdown(self, timeout: int = 0) -> None:
        raise NotImplementedError()

    def is_available(self) -> bool:
        raise NotImplementedError()


class RuntimeScope:
    def __init__(self, runtime: Runtime, shutdown_timeout: Optional[int] = None):
        self.runtime = runtime
        self.shutdown_timeout = shutdown_timeout

    def __enter__(self):
        return self

    def __exit__(self, *exc: Any):
        if self.shutdown_timeout is not None:
            self.runtime.shutdown(self.shutdown_timeout)
        else:
            self.runtime.shutdown()


class RunnerState:
    def __init__(self, config: Config, runtime: Runtime, tests: List[Test]):
        self.config = config
        self.runtime = runtime
        self.tests = tests
        self.results: Dict[str, Any] = {"failed": 0, "tested": 0}


DEFAULT_TEST_PATTERN = r"""
    # Credit: Tim Peters, et al. Python doctest.py
    # Test expression: PS1 line followed by zero or more PS2 lines
    (?P<expr>
        (?:^(?P<indent> [ ]*) {ps1} .*)   # PS1 line
        (?:\n           [ ]*  {ps2} .*)*  # PS2 lines
    )
    \n?
    # Expected result: any non-blank lines that don't start with PS1
    (?P<expected>
        (?:
        (?![ ]*$)      # Not a blank line
        (?![ ]*{ps1})  # Not a line starting with PS1
        .+$\n?         # But any other line
        )*
    )
"""


PYTHON_CONFIG = DEFAULT_CONFIG = Config(
    name="python",
    runtime="python",
    ps1=">>>",
    ps2="...",
    test_pattern=DEFAULT_TEST_PATTERN,
    blankline="|",
    match_types={},
)

CONFIG: Dict[str, Config] = {"python": PYTHON_CONFIG}

RUNTIME = {"python": "groktest.python.PythonRuntime"}


def init_runner_state(filename: str):
    contents = _read_file(filename)
    fm = _parse_front_matter(contents, filename)
    config = _config_for_front_matter(fm, filename)
    runtime = init_runtime(config)
    tests = parse_tests(contents, config, filename)
    return RunnerState(config, runtime, tests)


def _read_file(filename: str):
    return open(filename).read()


_FRONT_MATTER_P = re.compile(r"\s*^---\n(.*)\n---\n?$", re.MULTILINE | re.DOTALL)


def _parse_front_matter(s: str, filename: str) -> Any:
    """Parse front matter from string.

    Front matter can be defined using YAML, JSON, or INI.

    If PyYaml is installed, it's used to parse front matter. As this
    library has no external dependencies, if PyYaml is not installed, a
    parsing hack is used in attempt to parse front matter as YAML. In
    this case, front matter configuration is limited to simple key value
    pairs using `<key>: <value>` syntax.
    """
    m = _FRONT_MATTER_P.match(s)
    if not m:
        return {}
    fm = m.group(1)
    return (
        _try_parse_full_yaml(fm, filename)
        or _try_parse_json(fm, filename)
        or _try_parse_toml(fm, filename)
        or _try_parse_simplified_yaml(fm, filename)
        or {}
    )


def _try_parse_full_yaml(s: str, filename: str, raise_error: bool = False):
    try:
        import yaml  # type: ignore
    except ImportError:
        if raise_error:
            raise
        log.debug("yaml module not available, skipping full YAML for %s", filename)
        return None
    try:
        return yaml.safe_load(s)
    except Exception as e:
        if raise_error:
            raise
        log.debug("ERROR parsing YAML for %s: %s", filename, e)
        return None


def _try_parse_json(s: str, filename: str, raise_error: bool = False):
    try:
        return json.loads(s)
    except Exception as e:
        if raise_error:
            raise
        log.debug("ERROR parsing JSON for %s: %s", filename, e)
        return None


def _try_parse_toml(
    s: str, filename: str, raise_error: bool = False
) -> Optional[Dict[str, Any]]:
    from . import _vendor_tomli as toml

    try:
        return toml.loads(s)
    except toml.TOMLDecodeError as e:
        if raise_error:
            raise
        log.debug("ERROR parsing TOML for %s: %s", filename, e)
        return None


def _try_parse_simplified_yaml(
    s: str, filename: str, raise_error: bool = False
) -> Optional[Dict[str, Any]]:
    parser = configparser.ConfigParser()
    try:
        parser.read_string("[__anonymous__]\n" + s)
    except configparser.Error as e:
        if raise_error:
            raise
        log.debug("ERROR parsing INI for %s: %s", filename, e)
        return None
    else:
        parsed = {
            section: dict(
                {key: _simplified_yaml_val(val) for key, val in parser[section].items()}
            )
            for section in parser
        }
        return parsed.get("__anonymous__", {})


def _simplified_yaml_val(s: str):
    if s[:1] + s[-1:] in ("\"\"", "''"):
        return s[1:-1]
    s_lower = s.lower()
    if s_lower in ("true", "yes", "on"):
        return True
    if s_lower in ("false", "no", "off"):
        return False
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def _config_for_front_matter(fm: Any, filename: str):
    return (
        _default_config_for_missing_or_invalid_front_matter(fm, filename)
        or _config_for_test_type(fm, filename)
        or _explicit_config(fm, filename)
        or DEFAULT_CONFIG
    )


def _default_config_for_missing_or_invalid_front_matter(fm: Any, filename: str):
    if not fm:
        return DEFAULT_CONFIG
    if not isinstance(fm, dict):
        log.warning(
            "Unexpected front matter type %s in %s, expected map", type(fm), filename
        )
        return DEFAULT_CONFIG
    return None


def _config_for_test_type(fm: Dict[str, Any], filename: str):
    assert isinstance(fm, dict)
    test_type = fm.get("test-type")
    if not test_type:
        return None
    try:
        return CONFIG[test_type]
    except KeyError:
        raise TestTypeNotSupported(test_type) from None


def _explicit_config(fm: Any, filename: str):
    assert isinstance(fm, dict)
    config = fm.get("test-config")
    if not config:
        return None
    assert False, ("TODO", config)


def parse_tests(content: str, config: Config, filename: str):
    tests = []
    charpos = linepos = 0
    for m in config.test_pattern.finditer(content):
        linepos += content.count("\n", charpos, m.start())
        tests.append(_test_for_match(m, config, linepos, filename))
        linepos += content.count('\n', m.start(), m.end())
        charpos = m.end()
    return cast(List[Test], tests)


def _test_for_match(m: Match[str], config: Config, linepos: int, filename: str):
    expr = _format_expr(m, config, linepos, filename)
    expected = _format_expected(m, linepos, filename)
    return Test(expr, expected, filename, linepos + 1, {})


def _format_expr(m: Match[str], config: Config, linepos: int, filename: str):
    lines = _dedented_lines(
        m.group("expr"),
        len(m.group("indent")),
        linepos,
        filename,
    )
    return "\n".join(_strip_prompts(lines, config, linepos, filename))


def _strip_prompts(lines: List[str], config: Config, linepos: int, filename: str):
    return [
        _strip_prompt(line, config.ps1 if i == 0 else config.ps2, linepos + i, filename)
        for i, line in enumerate(lines)
    ]


def _strip_prompt(s: str, prompt: str, linepos: int, filename: str):
    assert s.startswith(prompt), (s, filename, linepos, prompt)
    prompt_len = len(prompt)
    if len(s) > prompt_len and s[prompt_len] != ' ':
        raise ValueError(
            f"File \"{filename}\", line {linepos + 1}, in test: "
            "space missing after prompt"
        )
    return s[prompt_len + 1 :]


def _format_expected(m: Match[str], linepos: int, filename: str):
    return "\n".join(
        _dedented_lines(
            m.group("expected"),
            len(m.group("indent")),
            linepos,
            filename,
        )
    )


def _dedented_lines(s: str, indent: int, linepos: int, filename: str):
    lines = s.split("\n")
    _strip_trailing_empty_line(lines)
    _check_test_indent(lines, indent, linepos, filename)
    return [line[indent:] for line in lines]


def _strip_trailing_empty_line(lines: List[str]):
    if len(lines) and not lines[-1].strip():
        lines.pop()


def _check_test_indent(lines: List[str], indent: int, linepos: int, filename: str):
    prefix = " " * indent
    for i, line in enumerate(lines):
        if line and not line.startswith(prefix):
            raise ValueError(
                f"File \"{filename}\", line {linepos + i + 1}, in test: "
                "inconsistent leading whitespace"
            )


def init_runtime(config: Config):
    try:
        import_spec = RUNTIME[config.runtime]
    except KeyError:
        raise RuntimeNotSupported(config.runtime)
    else:
        if "." not in import_spec:
            raise ValueError(config.runtime)
        modname, classname = import_spec.rsplit(".", 1)
        mod = importlib.import_module(modname)
        rt = getattr(mod, classname)()
        rt.init(config)
        return rt


def test_file(filename: str):
    result = _maybe_doctest(filename)
    if result is not None:
        return result

    state = init_runner_state(filename)
    with RuntimeScope(state.runtime):
        for test in state.tests:
            result = state.runtime.exec_test_expr(test)
            _handle_test_result(result, test, state)
        return state.results


def _handle_test_result(result: TestResult, test: Test, state: RunnerState):
    expected = _format_match_expected(test, state.config)
    test_output = _format_match_test_output(result, state.config)
    match = match_test_output(expected, test_output, state.config.match_types)
    _log_test_result_match(match, result, test, expected, test_output, state)
    if match:
        _handle_test_passed(test, match, state)
    else:
        _handle_test_failed(test, result, state)


def _format_match_expected(test: Test, config: Config):
    expected = _append_lf_for_non_empty(test.expected)
    return _remove_blankline_markers(expected, config.blankline)


def _append_lf_for_non_empty(s: str):
    return s + '\n' if s else s


def _remove_blankline_markers(s: str, marker: str):
    return re.sub(rf"(?m)^{re.escape(marker)}\s*?$", "", s)


def _format_match_test_output(result: TestResult, config: Config):
    # TODO: If there are any transforms to test output that are option
    # driven, etc
    return _truncate_empty_line_spaces(result.output)


def _truncate_empty_line_spaces(s: str):
    return re.sub(r"(?m)^[^\S\n]+$", "", s)


def match_test_output(
    expected: str,
    test_output: str,
    match_types: Optional[MatchTypes] = None,
    case_sensitive: bool = False,
):
    # TODO - lots of options here!
    # - is this a pattern match?
    # - is this an ellipsis match?
    # - is this some other type of match??

    m = parselib.parse(
        expected,
        test_output,
        {
            **_parselib_user_match_types(match_types or {}),
            **_parselib_builtin_match_types(),
        },
        evaluate_result=True,
        case_sensitive=case_sensitive,
    )
    return TestMatch(cast(parselib.Result, m).named) if m else None


def _parselib_user_match_types(match_types: MatchTypes):
    return {
        type_name: _parselib_regex_converter(pattern)
        for type_name, pattern in match_types.items()
    }


def _parselib_builtin_match_types():
    return {"pipe": _parselib_regex_converter(r"\|")}


def _parselib_regex_converter(pattern: str):
    def f(s: str):
        return s

    f.pattern = pattern
    return f


def _log_test_result_match(
    match: Optional[TestMatch],
    result: TestResult,
    test: Test,
    used_expected: str,
    used_test_output: str,
    state: RunnerState,
):
    log.debug("Result for %r", test.expr)
    log.debug("  match: %s", "yes" if match else "no")
    if match:
        log.debug("  bound variables: %s", match.bound_variables)
    log.debug("  test expected: %r", test.expected)
    log.debug("  test result: (%r) %r", result.code, result.output)
    log.debug("  used expected: %r", used_expected)
    log.debug("  used test output: %r", used_test_output)


def _handle_test_passed(test: Test, match: TestMatch, state: RunnerState):
    state.runtime.handle_bound_variables(match.bound_variables)
    state.results["tested"] += 1


def _handle_test_failed(test: Test, result: TestResult, state: RunnerState):
    _print_failed_test_sep()
    _print_failed_test(test, result, state.config)
    state.results["failed"] += 1
    state.results["tested"] += 1


def _print_failed_test_sep():
    print("**********************************************************************")


def _print_failed_test(test: Test, result: TestResult, config: Config):
    print(f"File \"{test.filename}\", line {test.line}")
    print("Failed example:")
    _print_test_expr(test.expr)
    if test.expected:
        print("Expected:")
        _print_test_expected(test.expected, config)
    else:
        print("Expected nothing")
    print("Got:")
    _print_test_result_output(result.output, config)


def _print_test_expr(s: str):
    for line in s.split("\n"):
        print("    " + line)


def _print_test_expected(s: str, config: Config):
    for line in s.split("\n"):
        print("    " + line)


def _print_test_result_output(output: str, config: Config):
    output = _format_test_result_output(output, config)
    for line in output.split("\n"):
        print("    " + line)


def _format_test_result_output(output: str, config: Config):
    output = _insert_blankline_markers(output, config.blankline)
    return _strip_trailing_lf(output)


def _insert_blankline_markers(s: str, marker: str):
    return re.sub(r"(?m)^[ ]*(?=\n)", marker, s)


def _strip_trailing_lf(s: str):
    return s[:-1] if s[-1:] == "\n" else s


def _maybe_doctest(filename: str):
    contents = _read_file(filename)
    fm = _parse_front_matter(contents, filename)
    if fm.get("test-type") == "doctest":
        failed, tested = _doctest_file(filename, fm)
        return {"failed": failed, "tested": tested}
    return None


def _doctest_file(filename: str, config: Any):
    import doctest

    return doctest.testfile(
        filename,
        module_relative=False,
        optionflags=_doctest_options(config),
        extraglobs=_doctest_globals(config),
    )


def _doctest_options(config: Any):
    opts = config.get("test-options")
    if not opts:
        return 0
    if not isinstance(opts, str):
        raise ValueError("doctest test-options must be a string")
    flags = 0
    for opt_flag, enabled in _iter_doctest_opts(opts):
        if enabled:
            flags |= opt_flag
        else:
            flags &= ~opt_flag
    return flags


def _iter_doctest_opts(opts: str) -> Generator[Tuple[int, bool], None, None]:
    import doctest

    for opt in re.findall(r"(?i)[+-][a-z0-9_]+", opts):
        assert opt[0] in ("+", "-"), (opt, opts)
        enabled, opt = opt[0] == "+", opt[1:]
        try:
            yield getattr(doctest, opt.upper()), enabled
        except AttributeError:
            pass


def _doctest_globals(config: Any):
    from pprint import pprint as pprint0

    def pprint(s: str, **kw: Any):
        kw = dict(width=72, **kw)
        pprint0(s, **kw)

    return {
        "pprint": pprint,
    }
