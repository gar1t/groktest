# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import *

import configparser
import importlib
import json
import logging
import os
import re

from . import _vendor_parse as parselib
from . import _vendor_tomli as toml

__all__ = [
    "DEFAULT_SPEC",
    "Error",
    "init_runner_state",
    "init_runtime",
    "match_test_output",
    "MatchTypes",
    "parse_tests",
    "ProjectDecodeError",
    "PYTHON_SPEC",
    "RunnerState",
    "Runtime",
    "RUNTIME",
    "RuntimeNotSupported",
    "test_file",
    "SPECS",
    "Test",
    "TestMatch",
    "TestResult",
    "TestSpec",
    "TestTypeNotSupported",
]

log = logging.getLogger("groktest")


class Error(Exception):
    pass


class TestTypeNotSupported(Error):
    pass


class RuntimeNotSupported(Error):
    pass


class ProjectDecodeError(Error):
    pass


class TestSpec:
    def __init__(
        self,
        runtime: str,
        ps1: str,
        ps2: str,
        test_pattern: str,
        blankline: str,
    ):
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
    def init(self, config: Optional[TestConfig] = None) -> None:
        raise NotImplementedError()

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
    def __init__(
        self,
        tests: List[Test],
        runtime: Runtime,
        spec: TestSpec,
        config: TestConfig,
        filename: str,
    ):
        self.tests = tests
        self.runtime = runtime
        self.spec = spec
        self.filename = filename
        self.config = config
        self.results: Dict[str, Any] = {"failed": 0, "tested": 0}


class DocTestRunnerState:
    def __init__(self, filename: str, config: TestConfig):
        self.filename = filename
        self.config = config


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


PYTHON_SPEC = DEFAULT_SPEC = TestSpec(
    runtime="python",
    ps1=">>>",
    ps2="...",
    test_pattern=DEFAULT_TEST_PATTERN,
    blankline="|",
)

Marker = Any

DOCTEST_MARKER: Marker = object()

SPECS: Dict[str, Union[TestSpec, Marker]] = {
    "python": PYTHON_SPEC,
    "doctest": DOCTEST_MARKER,
}

RUNTIME = {
    "doctest": "groktest.doctest.DoctestRuntime",
    "python": "groktest.python.PythonRuntime",
}

ProjectConfig = Dict[str, Any]

FrontMatter = Dict[str, Any]

TestConfig = Dict[str, Any]

TestOptions = Dict[str, Any]

MatchTypes = Dict[str, str]

FRONT_MATTER_TO_CONFIG = {
    "test-options": "options",
}


def init_runner_state(filename: str, project_config: Optional[ProjectConfig] = None):
    filename = os.path.abspath(filename)
    contents = _read_file(filename)
    fm = _parse_front_matter(contents, filename)
    spec = _spec_for_front_matter(fm, filename)
    test_config = _test_config(fm, project_config, filename)
    if spec is DOCTEST_MARKER:
        return DocTestRunnerState(filename, test_config)
    runtime = init_runtime(spec.runtime, test_config)
    tests = parse_tests(contents, spec, filename)
    return RunnerState(tests, runtime, spec, test_config, filename)


def _read_file(filename: str):
    return open(filename).read()


_FRONT_MATTER_P = re.compile(r"\s*^---\n(.*)\n---\n?$", re.MULTILINE | re.DOTALL)


def _parse_front_matter(s: str, filename: str) -> FrontMatter:
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
        or _empty_front_matter(filename)
    )


def _empty_front_matter(filename: str):
    log.debug("Missing or unparseable front matter for %s", filename)
    return cast(FrontMatter, {})


def _try_parse_full_yaml(s: str, filename: str, raise_error: bool = False):
    try:
        import yaml  # type: ignore
    except ImportError:
        if raise_error:
            raise
        log.debug("yaml module not available, skipping full YAML for %s", filename)
        return None
    try:
        data = yaml.safe_load(s)
    except Exception as e:
        if raise_error:
            raise
        log.debug("ERROR parsing YAML front matter for %s: %s", filename, e)
        return None
    else:
        log.debug("Parsed YAML front matter  for %s: %r", filename, data)
        return cast(FrontMatter, data)


def _try_parse_json(s: str, filename: str, raise_error: bool = False):
    try:
        data = json.loads(s)
    except Exception as e:
        if raise_error:
            raise
        log.debug("ERROR parsing JSON for %s: %s", filename, e)
        return None
    else:
        log.debug("Parsed JSON for %s: %r", filename, data)
        return cast(FrontMatter, data)


def _try_parse_toml(
    s: str, filename: str, raise_error: bool = False
) -> Optional[Dict[str, Any]]:
    try:
        data = toml.loads(s)
    except toml.TOMLDecodeError as e:
        if raise_error:
            raise
        log.debug("ERROR parsing TOML front matter for %s: %s", filename, e)
        return None
    else:
        log.debug("Parsed TOML front matter for %s: %r", filename, data)
        return cast(FrontMatter, data)


def _try_parse_simplified_yaml(
    s: str, filename: str, raise_error: bool = False
) -> Optional[Dict[str, Any]]:
    parser = configparser.ConfigParser()
    try:
        parser.read_string("[__anonymous__]\n" + s)
    except configparser.Error as e:
        if raise_error:
            raise
        log.debug("ERROR parsing simplified YAML for %s: %s", filename, e)
        return None
    else:
        data = _simplified_yaml_for_ini(parser)
        log.debug("Parsed simplified YAML front matter for %s: %r", filename, data)
        return cast(FrontMatter, data)


def _simplified_yaml_for_ini(parser: configparser.ConfigParser):
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


def _spec_for_front_matter(fm: Any, filename: str):
    return (
        _default_spec_for_missing_or_invalid_front_matter(fm, filename)
        or _spec_for_test_type(fm, filename)
        or _explicit_spec(fm, filename)
        or DEFAULT_SPEC
    )


def _default_spec_for_missing_or_invalid_front_matter(fm: Any, filename: str):
    if not fm:
        return DEFAULT_SPEC
    if not isinstance(fm, dict):
        log.warning(
            "Unexpected front matter type %s in %s, expected map", type(fm), filename
        )
        return DEFAULT_SPEC
    return None


def _spec_for_test_type(fm: Dict[str, Any], filename: str):
    assert isinstance(fm, dict)
    try:
        test_type = fm["tool"]["groktest"]["type"]
    except KeyError:
        test_type = fm.get("test-type")
    if not test_type:
        return None
    try:
        return SPECS[test_type]
    except KeyError:
        raise TestTypeNotSupported(test_type) from None


def _explicit_spec(fm: Any, filename: str):
    assert isinstance(fm, dict)
    spec = fm.get("test-spec")
    if not spec:
        return None
    if not isinstance(fm, dict):
        log.warning("Invalid 'test-spec' in %s: expected map", filename)
        return None
    try:
        return TestSpec(
            runtime=fm["runtime"],
            ps1=fm["ps1"],
            ps2=fm["ps2"],
            test_pattern=fm["test-pattern"],
            blankline=fm["blankline"],
        )
    except KeyError as e:
        log.warning(
            "Missing required attribute '%s', for 'test-spec' in %s",
            e.args[0],
            filename,
        )
        return None


def parse_tests(content: str, spec: TestSpec, filename: str):
    tests = []
    charpos = linepos = 0
    for m in spec.test_pattern.finditer(content):
        linepos += content.count("\n", charpos, m.start())
        tests.append(_test_for_match(m, spec, linepos, filename))
        linepos += content.count('\n', m.start(), m.end())
        charpos = m.end()
    return cast(List[Test], tests)


def _test_for_match(m: Match[str], spec: TestSpec, linepos: int, filename: str):
    expr = _format_expr(m, spec, linepos, filename)
    expected = _format_expected(m, linepos, filename)
    return Test(expr, expected, filename, linepos + 1, {})


def _format_expr(m: Match[str], spec: TestSpec, linepos: int, filename: str):
    lines = _dedented_lines(
        m.group("expr"),
        len(m.group("indent")),
        linepos,
        filename,
    )
    return "\n".join(_strip_prompts(lines, spec, linepos, filename))


def _strip_prompts(lines: List[str], spec: TestSpec, linepos: int, filename: str):
    return [
        _strip_prompt(line, spec.ps1 if i == 0 else spec.ps2, linepos + i, filename)
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


def _test_config(
    test_fm: FrontMatter,
    project_config: Optional[ProjectConfig],
    filename: str,
):
    project_config = project_config or _try_test_file_project_config(filename) or {}
    return _merge_test_config(project_config, test_fm)


def _merge_test_config(project_config: TestConfig, test_fm: FrontMatter) -> TestConfig:
    test_config = _normalize_front_matter(test_fm)
    # Start with project taking precedence over test config
    merged = {**test_config, **project_config}
    # Selectively merge/append test config back into result
    _merge_replace("options", test_fm, merged)
    _merge_append("python-init", test_fm, merged)
    return merged


def _normalize_front_matter(fm: FrontMatter) -> TestConfig:
    try:
        return fm["tool"]["groktest"]
    except KeyError:
        return _map_front_matter_option_names(fm)


def _map_front_matter_option_names(fm: FrontMatter) -> TestConfig:
    return {FRONT_MATTER_TO_CONFIG.get(name, name): fm[name] for name in fm}


def _merge_replace(name: str, src: Dict[str, Any], dest: Dict[str, Any]):
    try:
        src_val = src[name]
    except KeyError:
        pass
    else:
        dest[name] = src_val


def _merge_append(name: str, src: Dict[str, Any], dest: Dict[str, Any]):
    try:
        src_val = src[name]
    except KeyError:
        pass
    else:
        try:
            dest_val = dest[name]
        except KeyError:
            dest[name] = src_val
        else:
            dest[name] = _coerce_list(src_val) + _coerce_list(dest_val)


def _coerce_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else [x]


def _try_test_file_project_config(filename: str):
    for dirname in _iter_parents(filename):
        filename = os.path.join(dirname, "pyproject.toml")
        try:
            return load_project_config(filename)
        except FileNotFoundError:
            pass
        except ProjectDecodeError as e:
            log.warning("Error loading project config from %s: %s", filename, e)
            break
    return None


def _iter_parents(path: str):
    parent = last = os.path.dirname(path)
    while True:
        yield parent
        parent = os.path.dirname(parent)
        if parent == last:
            break
        last = parent


def init_runtime(name: str, config: Optional[TestConfig] = None):
    try:
        import_spec = RUNTIME[name]
    except KeyError:
        raise RuntimeNotSupported(name)
    else:
        if "." not in import_spec:
            raise ValueError(name)
        modname, classname = import_spec.rsplit(".", 1)
        mod = importlib.import_module(modname)
        rt = cast(Runtime, getattr(mod, classname)())
        rt.init(config)
        return rt


def test_file(filename: str, config: Optional[ProjectConfig] = None):
    state = init_runner_state(filename, config)
    if isinstance(state, DocTestRunnerState):
        return _doctest_file(state.filename, state.config)
    assert isinstance(state, RunnerState)
    with RuntimeScope(state.runtime):
        for test in state.tests:
            result = state.runtime.exec_test_expr(test)
            _handle_test_result(result, test, state)
        return state.results


def _handle_test_result(result: TestResult, test: Test, state: RunnerState):
    expected = _format_match_expected(test, state.spec)
    test_output = _format_match_test_output(result, test, state.spec)
    match = match_test_output(expected, test_output, test, state.spec)
    _log_test_result_match(match, result, test, expected, test_output, state)
    if match:
        _handle_test_passed(test, match, state)
    else:
        _handle_test_failed(test, result, state)


def _format_match_expected(test: Test, spec: TestSpec):
    expected = _append_lf_for_non_empty(test.expected)
    return _remove_blankline_markers(expected, spec.blankline)


def _append_lf_for_non_empty(s: str):
    return s + '\n' if s else s


def _remove_blankline_markers(s: str, marker: str):
    return re.sub(rf"(?m)^{re.escape(marker)}\s*?$", "", s)


def _format_match_test_output(result: TestResult, test: Test, spec: TestSpec):
    # TODO: If there are any transforms to test output that are option
    # driven, etc - use test config
    return _truncate_empty_line_spaces(result.output)


def _truncate_empty_line_spaces(s: str):
    return re.sub(r"(?m)^[^\S\n]+$", "", s)


def match_test_output(expected: str, test_output: str, test: Test, spec: TestSpec):
    matcher = _test_output_matcher(test, spec)
    return matcher(expected, test_output)


def _test_output_matcher(test: Test, spec: TestSpec):
    # TODO other matcher types:
    # - _StrMatcher (support normalize whitespace, case insensitive,
    #   ellipsis)

    # TODO default to _StrMatcher - use _ParserMatcher if +match

    # TODO test config options for _ParseMatcher: match types, case,
    # normalize whitspace

    return _ParseMatcher()


class _ParseMatcher:
    def __init__(
        self,
        match_types: Optional[MatchTypes] = None,
        case_sensitive: bool = True,
    ):
        self.match_types = match_types
        self.case_sensitive = case_sensitive

    def __call__(self, expected: str, test_output: str):
        m = parselib.parse(
            expected,
            test_output,
            {
                **_parselib_user_match_types(self.match_types or {}),
                **_parselib_builtin_match_types(),
            },
            evaluate_result=True,
            case_sensitive=self.case_sensitive,
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
    _print_failed_test(test, result, state.spec)
    state.results["failed"] += 1
    state.results["tested"] += 1


def _print_failed_test_sep():
    print("**********************************************************************")


def _print_failed_test(test: Test, result: TestResult, spec: TestSpec):
    print(f"File \"{test.filename}\", line {test.line}")
    print("Failed example:")
    _print_test_expr(test.expr)
    if test.expected:
        print("Expected:")
        _print_test_expected(test.expected, spec)
    else:
        print("Expected nothing")
    print("Got:")
    _print_test_result_output(result.output, spec)


def _print_test_expr(s: str):
    for line in s.split("\n"):
        print("    " + line)


def _print_test_expected(s: str, spec: TestSpec):
    for line in s.split("\n"):
        print("    " + line)


def _print_test_result_output(output: str, spec: TestSpec):
    output = _format_test_result_output(output, spec)
    for line in output.split("\n"):
        print("    " + line)


def _format_test_result_output(output: str, spec: TestSpec):
    output = _insert_blankline_markers(output, spec.blankline)
    return _strip_trailing_lf(output)


def _insert_blankline_markers(s: str, marker: str):
    return re.sub(r"(?m)^[ ]*(?=\n)", marker, s)


def _strip_trailing_lf(s: str):
    return s[:-1] if s[-1:] == "\n" else s


def _doctest_file(filename: str, config: TestConfig):
    import doctest

    failed, tested = doctest.testfile(
        filename,
        module_relative=False,
        optionflags=_doctest_options(config),
        extraglobs=_doctest_globals(config),
    )
    return {"failed": failed, "tested": tested}


def _doctest_options(config: TestConfig):
    opts = config.get("options")
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


def load_project_config(filename: str):
    try:
        data = _load_toml(filename)
    except toml.TOMLDecodeError as e:
        raise ProjectDecodeError(e, filename) from None
    else:
        return _project_config_for_data(data) if data else None


def _load_toml(filename: str):
    try:
        f = open(filename, "rb")
    except FileNotFoundError:
        raise
    with f:
        try:
            data = toml.load(f)
        except toml.TOMLDecodeError:
            raise
        else:
            log.debug("using project config in %s", filename)
            data["__src__"] = filename
            return data


def _project_config_for_data(data: Dict[str, Any]):
    try:
        groktest_data = data["tool"]["groktest"]
    except KeyError:
        return None
    else:
        groktest_data["__src__"] = data["__src__"]
        return cast(ProjectConfig, groktest_data)
