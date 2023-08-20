# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import *

import importlib
import json
import configparser
import logging
import re

from . import _vendor_parse as parselib

__all__ = [
    "Config",
    "CONFIG",
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
    "TestSource",
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
        self.match_types = match_types

    def __str__(self):
        return f"<groktest.Config '{self.name}'>"


class TestSource:
    def __init__(self, filename: str, line: int):
        self.filename = filename
        self.line = line


class Test:
    def __init__(self, expr: str, expected: str, source: TestSource):
        self.expr = expr
        self.expected = expected
        self.source = source


class TestResult:
    def __init__(self, code: int, output: str):
        self.code = code
        self.output = output


class TestMatch:
    def __init__(self, bound_variables: Dict[str, Any]):
        self.bound_variables = bound_variables


class Runtime:
    def run_test(self, test: Test) -> TestResult:
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
        or _try_parse_ini(fm, filename)
        or _try_parse_simple_yaml(fm, filename)
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


def _try_parse_ini(
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
            section: dict({key: _ini_val(val) for key, val in parser[section].items()})
            for section in parser
        }
        anon = parsed.pop("__anonymous__", {})
        defaults = parsed.pop("DEFAULT", None)
        return {**anon, **parsed, **({"DEFAULT": defaults} if defaults else {})}


def _ini_val(s: str):
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


def _try_parse_simple_yaml(s: str, filename: str, raise_error: bool = False):
    # INI format resembles YAML when ':' key/val delimiter is used
    return _try_parse_ini(s, filename, raise_error)


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
        raise TestTypeNotSupported(test_type)


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
    return Test(expr, expected, TestSource(filename, linepos + 1))


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
    if s[prompt_len] != ' ':
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
    # Until Groktest supports doctest format, punt to real doctest
    result = _maybe_doctest_bootstrap(filename)
    if result is not None:
        return result

    state = init_runner_state(filename)
    with RuntimeScope(state.runtime):
        for test in state.tests:
            result = state.runtime.run_test(test)
            _handle_test_result(result, test, state)
        return state.results


def _handle_test_result(result: TestResult, test: Test, state: RunnerState):
    match = match_test_output(test.expected, result.output, state.config.match_types)
    if match:
        _handle_test_passed(test, match, state)
    else:
        _handle_test_failed(test, result, state)


def match_test_output(
    expected: str,
    test_output: str,
    match_types: Optional[MatchTypes] = None,
    case_sensitive: bool = False,
):
    m = parselib.parse(
        expected,
        test_output,
        _parselib_match_types(match_types or {}),
        evaluate_result=True,
        case_sensitive=case_sensitive,
    )
    return TestMatch(cast(parselib.Result, m).named) if m else None


def _parselib_match_types(match_types: MatchTypes):
    return {
        type_name: _parselib_regex_converter(pattern)
        for type_name, pattern in match_types.items()
    }


def _parselib_regex_converter(pattern: str):
    def f(s: str):
        return s

    f.pattern = pattern
    return f


def _handle_test_passed(test: Test, match: TestMatch, state: RunnerState):
    state.runtime.handle_bound_variables(match.bound_variables)
    state.results["tested"] += state.results["tested"]


def _handle_test_failed(test: Test, result: TestResult, state: RunnerState):
    print("Some test failed")
    print(f"Expected: {test.expected}")
    print(f"Got: {result.output}")
    state.results["failed"] += state.results["failed"]
    state.results["tested"] += state.results["tested"]


def _maybe_doctest_bootstrap(filename: str):
    contents = _read_file(filename)
    fm = _parse_front_matter(contents, filename)
    if fm.get("test-type") == "doctest":
        failed, tested = _doctest_file(filename)
        return {"failed": failed, "tested": tested}
    return None


def _doctest_file(filename: str):
    import doctest
    from pprint import pprint as pprint0

    def pprint(s: str, **kw: Any):
        kw = dict(width=72, **kw)
        pprint0(s, **kw)

    options = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
    globs = {"pprint": pprint}
    return doctest.testfile(
        filename,
        module_relative=False,
        optionflags=options,
        extraglobs=globs,
    )
