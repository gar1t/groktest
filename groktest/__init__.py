# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import *
from types import ModuleType

import configparser
import copy
import difflib
import importlib
import importlib.util
import inspect
import io
import json
import logging
import os
import re
import sys
import tokenize

from . import _vendor_parse as parselib
from . import _vendor_tomli as toml

__all__ = [
    "DEFAULT_SPEC",
    "PYTHON_SPEC",
    "RUNTIME",
    "Error",
    "ParseTypeFunction",
    "ParseTypeFunctions",
    "ParseTypes",
    "ProjectDecodeError",
    "RunnerState",
    "Runtime",
    "RuntimeNotSupported",
    "SPECS",
    "Test",
    "TestMatch",
    "TestMatcher",
    "TestResult",
    "TestSpec",
    "TestTypeNotSupported",
    "init_runner_state",
    "match_test_output",
    "parse_tests",
    "start_runtime",
    "test_file",
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


ProjectConfig = Dict[str, Any]

FrontMatter = Dict[str, Any]

TestConfig = Dict[str, Any]

TestOptions = Dict[str, Any]

ParseTypes = Dict[str, str]

ParseTypeFunction = Callable[[str], Any]

ParseTypeFunctions = Dict[str, ParseTypeFunction]


class TestSpec:
    def __init__(
        self,
        runtime: str,
        ps1: str,
        ps2: str,
        test_pattern: str,
        blankline: str,
        wildcard: str,
        option_candidates: Union[None, str, Callable[[str], Iterator[str]]],
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
        self.wildcard = wildcard
        self.option_candidates = option_candidates


TestOptions = Dict[str, Any]


class TestMatch:
    def __init__(
        self,
        match: bool,
        vars: Optional[Dict[str, Any]] = None,
        reason: Optional[Any] = None,
    ):
        self.match = match
        self.vars = vars
        self.reason = reason


TestMatcher = Callable[
    [
        str,
        str,
        Optional[TestOptions],
        Optional[TestConfig],
    ],
    TestMatch,
]


class Test:
    def __init__(
        self,
        expr: str,
        expected: str,
        filename: str,
        line: int,
        options: TestOptions,
    ):
        self.expr = expr
        self.expected = expected
        self.filename = filename
        self.line = line
        self.options = options


class TestResult:
    def __init__(self, code: int, output: str, short_error: Optional[str] = None):
        self.code = code
        self.output = output
        self.short_error = short_error


class Runtime:
    def start(self, config: Optional[TestConfig] = None) -> None:
        raise NotImplementedError()

    def init_for_tests(self, config: Optional[TestConfig] = None) -> None:
        raise NotImplementedError()

    def exec_test_expr(self, test: Test, options: TestOptions) -> TestResult:
        raise NotImplementedError()

    def handle_test_match(self, match: TestMatch) -> None:
        raise NotImplementedError()

    def stop(self, timeout: int = 0) -> None:
        raise NotImplementedError()

    def is_available(self) -> bool:
        raise NotImplementedError()


class RuntimeScope:
    def __init__(self, runtime: Runtime, stop_timeout: Optional[int] = None):
        self.runtime = runtime
        self.stop_timeout = stop_timeout

    def __enter__(self):
        return self

    def __exit__(self, *exc: Any):
        if self.stop_timeout is not None:
            self.runtime.stop(self.stop_timeout)
        else:
            self.runtime.stop()


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
        self.results: Dict[str, Any] = {"failed": 0, "tested": 0, "skipped": 0}
        self.skip_rest = False


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

OPTIONS_PATTERN = re.compile(
    r"[+]([\w\-]+)(?:\s*=\s*((?:'.*?')|(?:\".*?\")|(?:[^ $]+)))?|[-]([\w\-]+)"
)


def _python_comments(s: str):
    file = io.StringIO(s)
    for token in tokenize.generate_tokens(file.readline):
        type, val = token[:2]
        if type == tokenize.COMMENT:
            yield val


PYTHON_SPEC = DEFAULT_SPEC = TestSpec(
    runtime="python",
    ps1=">>>",
    ps2="...",
    test_pattern=DEFAULT_TEST_PATTERN,
    blankline="⤶",
    wildcard="...",
    option_candidates=_python_comments,
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


def init_runner_state(filename: str, project_config: Optional[ProjectConfig] = None):
    filename = os.path.abspath(filename)
    contents = _read_file(filename)
    fm = _parse_front_matter(contents, filename)
    spec = _spec_for_front_matter(fm, filename)
    test_config = _test_config(fm, project_config, filename)
    log.debug("test config: %s", test_config)
    if spec is DOCTEST_MARKER:
        return DocTestRunnerState(filename, test_config)
    runtime = start_runtime(spec.runtime, test_config)
    tests = parse_tests(contents, spec, filename)
    return RunnerState(tests, runtime, spec, test_config, filename)


def init_test_runner_state(spec: TestSpec, filename: Optional[str] = None):
    runtime = start_runtime(spec.runtime)
    return RunnerState([], runtime, spec, {}, filename or "<test>")


def _read_file(filename: str):
    bytes = open(filename, "rb").read()
    return _norm_line_endings(bytes).decode()


def _norm_line_endings(b: bytes):
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


_FRONT_MATTER_P = re.compile(r"\s*^---\n(.*)\n---\n?$", re.MULTILINE | re.DOTALL)


def _parse_front_matter(s: str, filename: str):
    """Parse front matter from string.

    Front matter can be defined using YAML, JSON, or INI.

    If PyYaml is installed, it's used to parse front matter. As this
    library has no external dependencies, if PyYaml is not installed, a
    parsing hack is used in attempt to parse front matter as YAML. In
    this case, front matter configuration is limited to simple key value
    pairs using `<key>: <value>` syntax.
    """
    data = _parsed_front_matter(s, filename) or _empty_front_matter(filename)
    data["__src__"] = filename
    return data


def _parsed_front_matter(s: str, filename: str):
    m = _FRONT_MATTER_P.match(s)
    if not m:
        return None
    fm = m.group(1)
    return (
        _try_parse_json(fm, filename)
        or _try_parse_toml(fm, filename)
        or _try_parse_full_yaml(fm, filename)
        or _try_parse_simplified_yaml(fm, filename)
    )


def _empty_front_matter(filename: str):
    log.debug("Missing or unparsable front matter for %s", filename)
    return cast(FrontMatter, {})


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


def _try_parse_toml(s: str, filename: str, raise_error: bool = False):
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
        if not isinstance(data, dict):
            log.warning(
                "Unsupported front-matter in %s: expected mapping, got %s",
                filename,
                type(data).__name__,
            )
            return None
        return cast(FrontMatter, data)


def _try_parse_simplified_yaml(s: str, filename: str, raise_error: bool = False):
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


def parse_tests(content: str, spec: TestSpec, filename: str):
    tests = []
    charpos = linepos = 0
    for m in spec.test_pattern.finditer(content):
        linepos += content.count("\n", charpos, m.start())
        tests.append(_test_for_match(m, spec, linepos, filename))
        linepos += content.count('\n', m.start(), m.end())
        charpos = m.end()
    return cast(List[Test], tests)


def _test_for_match(m: re.Match[str], spec: TestSpec, linepos: int, filename: str):
    expr = _format_expr(m, spec, linepos, filename)
    options = _parse_test_options(expr, spec)
    expected = _format_expected(m, linepos, filename)
    return Test(expr, expected, filename, linepos + 1, options)


def _format_expr(m: re.Match[str], spec: TestSpec, linepos: int, filename: str):
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


def _parse_test_options(expr: str, spec: TestSpec):
    options: Dict[str, Any] = {}
    for part in _test_option_candidates(expr, spec):
        options.update(_decode_options(part))
    return options


def _test_option_candidates(s: str, spec: TestSpec) -> Sequence[str]:
    if not spec.option_candidates:
        return []
    if callable(spec.option_candidates):
        return list(spec.option_candidates(s))
    return [m.group(1) for m in re.finditer(spec.option_candidates, s)]


def _format_expected(m: re.Match[str], linepos: int, filename: str):
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
    test_config = front_matter_to_config(test_fm)
    # Start with project taking precedence over test config
    merged = {
        **copy.deepcopy(test_config),
        **copy.deepcopy(project_config),
    }
    # Selectively merge/append test config back into result
    _merge_append_list(["options"], test_config, merged)
    _merge_append_list(["python", "init"], test_config, merged)
    _merge_items(["parse", "types"], test_config, merged)
    _merge_append_list(["__src__"], test_config, merged)
    return merged


def front_matter_to_config(fm: FrontMatter) -> TestConfig:
    try:
        return fm["tool"]["groktest"]
    except KeyError:
        return _mapped_front_matter_config(fm)


FRONT_MATTER_TO_CONFIG = {
    "parse-types": ["parse", "types"],
    "parse-functions": ["parse", "functions"],
    "python-init": ["python", "init"],
    "test-options": ["options"],
}


def _mapped_front_matter_config(fm: FrontMatter) -> TestConfig:
    config = {}
    for name in fm:
        config_path = FRONT_MATTER_TO_CONFIG.get(name, [name])
        target = config
        for part in config_path[:-1]:
            target = config.setdefault(part, {})
        target[config_path[-1]] = fm[name]
    return config


def _merge_replace(path: List[str], src: Dict[str, Any], dest: Dict[str, Any]):
    key, val, merge_dest = _merge_kv_dest(path, src, dest)
    if not key:
        return
    assert merge_dest
    merge_dest[key] = val


def _merge_kv_dest(
    path: List[str],
    src: Dict[str, Any],
    dest: Dict[str, Any],
) -> Union[Tuple[None, None, None], Tuple[str, Any, Dict[str, Any]]]:
    cur_src = src
    for key in path[:-1]:
        try:
            cur_src = src[key]
        except KeyError:
            return None, None, None
    try:
        val = cur_src[path[-1]]
    except KeyError:
        return None, None, None

    cur_dest = dest
    for key in path[:-1]:
        cur_dest = cur_dest.setdefault(key, {})
        if not isinstance(cur_dest, dict):
            return None, None, None

    return path[-1], val, cur_dest


def _merge_append_list(path: List[str], src: Dict[str, Any], dest: Dict[str, Any]):
    key, src_val, append_dest = _merge_kv_dest(path, src, dest)
    if not key:
        return
    assert append_dest
    append_dest[key] = _coerce_list(src_val) + _coerce_list(append_dest.get(key))


def _merge_items(path: List[str], src: Dict[str, Any], dest: Dict[str, Any]):
    key, src_val, merge_dest = _merge_kv_dest(path, src, dest)
    if not key:
        return
    assert merge_dest
    merge_dest.setdefault(key, {}).update(src_val)


def _coerce_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else [] if x is None else [x]


def _try_test_file_project_config(filename: str):
    for dirname in _iter_parents(filename):
        path = os.path.join(dirname, "pyproject.toml")
        try:
            return load_project_config(path)
        except FileNotFoundError:
            pass
        except ProjectDecodeError as e:
            log.warning("Error loading project config from %s: %s", path, e)
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


def start_runtime(name: str, config: Optional[TestConfig] = None):
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
        rt.start(config)
        return rt


def test_file(filename: str, config: Optional[ProjectConfig] = None):
    state = init_runner_state(filename, config)
    if isinstance(state, DocTestRunnerState):
        return _doctest_file(state.filename, state.config)
    assert isinstance(state, RunnerState)
    assert state.runtime.is_available
    state.runtime.init_for_tests(state.config)
    _apply_skip_for_solo(state.tests)
    with RuntimeScope(state.runtime):
        for test in state.tests:
            test_options = _test_options(test, state.config, state.spec)
            _apply_skip_rest(test_options, state)
            if _skip_test(test_options, state):
                _handle_test_skipped(test, state)
            else:
                run_test(test, test_options, state)
        return state.results


def run_test(test: Test, options: TestOptions, state: RunnerState):
    result = state.runtime.exec_test_expr(test, options)
    _handle_test_result(result, test, options, state)


def _apply_skip_for_solo(tests: List[Test]):
    solo_tests = [test for test in tests if test.options.get("solo")]
    if not solo_tests:
        return
    for test in tests:
        test.options["skip"] = test not in solo_tests


def _apply_skip_rest(options: TestOptions, state: RunnerState):
    state.skip_rest = _option_value("skiprest", options, state.skip_rest)


def _skip_test(options: TestOptions, state: RunnerState):
    return _option_value("skip", options, state.skip_rest)


def _handle_test_skipped(test: Test, state: RunnerState):
    state.results["skipped"] += 1


def _handle_test_result(
    result: TestResult, test: Test, options: TestOptions, state: RunnerState
):
    expected = _format_match_expected(test, options, state.spec)
    output_candidates = _match_test_output_candidates(result, test, options)
    match = _try_match_output_candidates(output_candidates, expected, test, state)
    if options.get("fails"):
        if match.match:
            _handle_unexpected_test_pass(test, options, state)
        else:
            _handle_expected_test_failed(test, state)
    elif match.match:
        _handle_test_passed(test, match, state)
    else:
        _handle_test_failed(test, match, result, options, state)


def _try_match_output_candidates(
    output_candidates: List[str], expected: str, test: Test, state: RunnerState
):
    assert output_candidates
    match = None
    for output in output_candidates:
        match = match_test_output(expected, output, test, state.config, state.spec)
        if match.match:
            return match
    assert match
    return match


def _handle_unexpected_test_pass(test: Test, options: TestOptions, state: RunnerState):
    _print_failed_test_sep(options)
    print(f"File \"{test.filename}\", line {test.line}")
    print("Failed example:")
    _print_test_expr(test.expr)
    print("Expected test to fail but passed")
    state.results["failed"] += 1
    state.results["tested"] += 1


def _handle_expected_test_failed(test: Test, state: RunnerState):
    state.results["tested"] += 1


def _format_match_expected(test: Test, options: TestOptions, spec: TestSpec):
    expected = _append_lf_for_non_empty(test.expected)
    expected = _maybe_remove_blankline_markers(expected, options, spec)
    expected = _maybe_normalize_whitespace(expected, options)
    expected = _maybe_normalize_paths(expected, options)
    return expected


def _append_lf_for_non_empty(s: str):
    return s + '\n' if s else s


def _maybe_remove_blankline_markers(s: str, options: TestOptions, spec: TestSpec):
    marker = _blankline_marker(options, spec)
    if not marker:
        return s
    return _remove_blankline_markers(s, marker)


def _blankline_marker(options: TestOptions, spec: TestSpec):
    opt_val = options.get("blankline")
    if opt_val is None or opt_val is True:
        return spec.blankline
    if not opt_val:
        return None
    return opt_val


def _remove_blankline_markers(s: str, marker: str):
    return re.sub(rf"(?m)^{re.escape(marker)}\s*?$", "", s)


def _maybe_normalize_whitespace(s: str, options: TestOptions):
    keep_whitespace = _option_value("space", options, True)
    if keep_whitespace:
        return s
    return " ".join(s.split())


def _maybe_normalize_paths(s: str, options: TestOptions):
    if not _option_value("paths", options, False):
        return s
    return s.replace("\\\\", "\\").replace("\\", "/")


def _match_test_output_candidates(result: TestResult, test: Test, options: TestOptions):
    output = _format_test_output(result.output, options)
    short_error = _maybe_short_error(result, options)
    if short_error:
        return [output, _format_test_output(short_error, options)]
    return [output]


def _format_test_output(output: str, options: TestOptions):
    output = _truncate_empty_line_spaces(output)
    output = _maybe_normalize_whitespace(output, options)
    output = _maybe_normalize_paths(output, options)
    return output


def _maybe_short_error(result: TestResult, options: TestOptions):
    if result.short_error and not _option_value("error-detail", options, False):
        return result.short_error
    return None


def _truncate_empty_line_spaces(s: str):
    return re.sub(r"(?m)^[^\S\n]+$", "", s)


def match_test_output(
    expected: str,
    test_output: str,
    test: Test,
    config: TestConfig,
    spec: TestSpec,
):
    options = _test_options(test, config, spec)
    return matcher(options)(expected, test_output, options, config)


def _test_options(test: Test, config: TestConfig, spec: TestSpec):
    options = {
        **_parse_config_options(config, test.filename),
        **test.options,
    }
    _maybe_apply_spec_wildcard(spec, options)
    return cast(TestOptions, options)


def _parse_config_options(config: TestConfig, filename: str):
    parsed: TestOptions = {}
    options = config.get("options")
    if not options:
        return parsed
    for part in _coerce_list(options):
        if not isinstance(part, str):
            log.warning("Invalid option %r in %s: expected string", part, filename)
            continue
        parsed.update(_decode_options(part))
    return parsed


def _decode_options(s: str) -> Dict[str, Any]:
    return dict(_name_val_for_option_match(m) for m in OPTIONS_PATTERN.finditer(s))


def _name_val_for_option_match(m: re.Match[str]) -> Tuple[str, Any]:
    plus_name, plus_val, neg_name = m.groups()
    if neg_name:
        assert plus_name is None and plus_val is None, m
        return neg_name, False
    else:
        assert neg_name is None, m
        return plus_name, True if plus_val is None else _parse_option_val(plus_val)


def _parse_option_val(s: str):
    return _simplified_yaml_val(s)


def _maybe_apply_spec_wildcard(spec: TestSpec, options: TestOptions):
    if options.get("wildcard") is True:
        options["wildcard"] = spec.wildcard


def matcher(options: TestOptions) -> TestMatcher:
    if options.get("parse"):
        return parse_match
    return str_match


def parse_match(
    expected: str,
    test_output: str,
    options: Optional[TestOptions] = None,
    config: Optional[TestConfig] = None,
):
    options = options or {}
    config = config or {}
    case_sensitive = _option_value("case", options, True)
    extra_types = _parselib_types(config)
    try:
        m = parselib.parse(
            expected,
            test_output,
            extra_types,
            evaluate_result=True,
            case_sensitive=case_sensitive,
        )
    except ValueError as e:
        return TestMatch(False, None, e)
    else:
        if m:
            return TestMatch(True, cast(parselib.Result, m).named)
        return TestMatch(False)


def _option_value(name: str, options: Dict[str, Any], default: Any):
    try:
        val = options[name]
    except KeyError:
        return default
    else:
        if val is None:
            return default
        return val


def _parselib_types(config: TestConfig) -> ParseTypeFunctions:
    return {
        **_parselib_module_types(config),
        **_parselib_regex_types(config),
    }


def _parselib_module_types(config: TestConfig) -> ParseTypeFunctions:
    try:
        functions_spec = config["parse"]["functions"]
    except KeyError:
        return {}
    else:
        functions_spec = _coerce_list(functions_spec)
        path = _config_src_path(config)
        return dict(_iter_parse_functions(functions_spec, path))


def _config_src_path(config: TestConfig):
    config_src: List[str] = _coerce_list(config["__src__"])
    return [os.path.dirname(path) for path in config_src]


def _iter_parse_functions(
    specs: List[Any],
    path: List[str],
) -> Generator[Tuple[str, ParseTypeFunction], None, None]:
    for spec in specs:
        log.debug("Loading parse functions from %s", spec)
        module = _try_load_module(spec, path)
        if not module:
            continue
        found = 0
        for f in _iter_module_parse_functions(module):
            found += 1
            type_name = _parse_type_name(f)
            log.debug("Registering function %s as '%s' type", f.__name__, type_name)
            yield type_name, f
        if not found:
            log.debug("No parse functions found in %s", spec)


def _try_load_module(spec: str, path: List[str]):
    if not isinstance(spec, str):
        log.warning("Invalid value for type-functions %r, expected a string", spec)
        return None
    _ensure_sys_path_for_doc_tests(path)
    try:
        return importlib.import_module(spec)
    except Exception as e:
        if log.getEffectiveLevel() <= logging.DEBUG:
            log.exception("Loading module %r", spec)
        else:
            log.warning("Error loading parse functions from %r: %r", spec, e)
        return None


def _ensure_sys_path_for_doc_tests(doctest_path: List[str]):
    # Add in reverse order as doctest path goes from more specific (test
    # file path) to less specific (project path)
    for p in reversed(doctest_path):
        if p not in sys.path:
            sys.path.append(p)


def _parse_type_name(f: Callable[[str], Any]):
    try:
        return getattr(f, "type_name")
    except AttributeError:
        name = f.__name__
        assert name.startswith("parse_")
        return name[6:]


def _iter_module_parse_functions(
    module: ModuleType,
) -> Generator[ParseTypeFunction, None, None]:
    for name in _module_parse_names(module):
        x = getattr(module, name)

        if _is_parse_function(x):
            yield x


def _module_parse_names(module: ModuleType):
    all = getattr(module, "__all__", [])
    if isinstance(all, str):
        all = all.split()
    return [name for name in (all or dir(module)) if name.startswith("parse_")]


def _is_parse_function(x: Any):
    # Simple sniff test for callable with at least one arg
    try:
        sig = inspect.signature(x)
    except TypeError:
        return False
    else:
        return len(sig.parameters) >= 1


def _parselib_regex_types(config: TestConfig) -> ParseTypeFunctions:
    try:
        types = config["parse"]["types"]
    except KeyError:
        return {}
    else:
        return {
            type_name: _parselib_regex_converter(pattern)
            for type_name, pattern in types.items()
        }


def _parselib_regex_converter(pattern: str):
    def f(s: str):
        return s

    f.pattern = pattern
    return f


def str_match(
    expected: str,
    test_output: str,
    options: Optional[TestOptions] = None,
    config: Optional[TestConfig] = None,
):
    options = options or {}
    expected, test_output = _apply_transform_options(expected, test_output, options)
    wildcard = options.get("wildcard")
    if wildcard:
        return _wildcard_match(expected, test_output, wildcard, options)
    return _default_str_match(expected, test_output, options)


def _apply_transform_options(expected: str, test_output: str, options: TestOptions):
    for f in [_apply_case_option]:
        expected, test_output = f(expected, test_output, options)
    return expected, test_output


def _apply_case_option(expected: str, test_output: str, options: TestOptions):
    if _option_value("case", options, True):
        return expected, test_output
    return expected.lower(), test_output.lower()


def _wildcard_match(
    expected: str,
    test_output: str,
    wildcard: str,
    options: Optional[TestOptions],
):
    # Credit: Python doctest authors
    expected_parts = expected.split(wildcard)
    if len(expected_parts) == 1:
        return TestMatch(expected == test_output)

    # Match prior to first wildcard
    startpos, endpos = 0, len(test_output)
    expected_part = expected_parts[0]
    if expected_part:
        if not test_output.startswith(expected_part):
            return TestMatch(False)
        startpos = len(expected_part)
        del expected_parts[0]

    # Match after last wildcard
    expected_part = expected_parts[-1]
    if expected_part:
        if not test_output.endswith(expected_part):
            return TestMatch(False)
        endpos -= len(expected_part)
        del expected_parts[-1]

    if startpos > endpos:
        # Exact end matches required more characters than we have, as in
        # _wildcard_match('aa...aa', 'aaa')
        return TestMatch(False)

    # For the rest, find the leftmost non-overlapping match for each
    # part. If there's no overall match that way alone, there's no
    # overall match period.
    for expected_part in expected_parts:
        startpos = test_output.find(expected_part, startpos, endpos)
        if startpos < 0:
            return TestMatch(False)
        startpos += len(expected_part)

    return TestMatch(True)


def _default_str_match(
    expected: str,
    test_output: str,
    options: Optional[TestOptions] = None,
):
    return TestMatch(True) if test_output == expected else TestMatch(False)


def _log_test_result_match(
    match: TestMatch,
    result: TestResult,
    test: Test,
    used_expected: str,
    used_test_output: str,
    state: RunnerState,
):
    log.debug("Result for %r", test.expr)
    log.debug("  match: %s", "yes" if match.match else "no")
    if match.match:
        log.debug("  match vars: %s", match.vars)
    log.debug("  test expected: %r", test.expected)
    log.debug("  test output: (%r) %r", result.code, result.output)
    log.debug("  used expected: %r", used_expected)
    log.debug("  used output: %r", used_test_output)


def _handle_test_passed(test: Test, match: TestMatch, state: RunnerState):
    state.runtime.handle_test_match(match)
    state.results["tested"] += 1


def _handle_test_failed(
    test: Test,
    match: TestMatch,
    result: TestResult,
    options: TestOptions,
    state: RunnerState,
):
    _print_failed_test_sep(options)
    _print_failed_test(test, match, result, options, state.spec)
    state.results["failed"] += 1
    state.results["tested"] += 1


def _print_failed_test_sep(options: TestOptions):
    sep = _option_value("sep", options, True)
    if sep is True:
        print("**********************************************************************")
    elif sep:
        print(sep)


def _print_failed_test(
    test: Test,
    match: TestMatch,
    result: TestResult,
    options: TestOptions,
    spec: TestSpec,
):
    print(f"File \"{test.filename}\", line {test.line}")
    print("Failed example:")
    _print_test_expr(test.expr)
    if test.expected and options.get("diff"):
        _print_test_result_diff(test, result, options, spec)
    else:
        _print_test_expected(test)
        _print_test_result_output(result, options, spec)
    if match.reason:
        print(f"Reason:")
        _print_mismatch_reason(match.reason, test)


def _print_test_expr(expr: str):
    expr = expr.strip()
    for line in expr.split("\n"):
        print("    " + line)


def _print_test_result_diff(
    test: Test,
    result: TestResult,
    options: TestOptions,
    spec: TestSpec,
):
    expected_lines, output_lines = _format_lines_for_diff(test, result, options, spec)
    print("Differences between expected and actual:")
    for line in _diff_lines(expected_lines, output_lines):
        print("   " + line)


def _format_lines_for_diff(
    test: Test, result: TestResult, options: TestOptions, spec: TestSpec
):
    expected = test.expected
    output = _format_test_result_output(result.output, options, spec)
    return (expected.split("\n"), output.split("\n"))


def _diff_lines(a: List[str], b: List[str]):
    diff = difflib.unified_diff(a, b, n=2)
    diff_no_header = list(diff)[2:]
    for line in diff_no_header:
        yield line.rstrip()


def _print_test_expected(test: Test):
    if test.expected:
        print("Expected:")
        expected = _format_test_result_expected(test.expected)
        for line in expected.split("\n"):
            print("    " + line)
    else:
        print("Expected nothing")


def _format_test_result_expected(expected: str):
    return expected.strip()


def _print_test_result_output(result: TestResult, options: TestOptions, spec: TestSpec):
    if result.output:
        print("Got:")
        output = _format_test_result_output(result.output, options, spec)
        for line in output.split("\n"):
            print("    " + line)
    else:
        print("Got nothing")


def _format_test_result_output(output: str, options: TestOptions, spec: TestSpec):
    blankline = _blankline_marker(options, spec)
    if blankline:
        output = _insert_blankline_markers(output, blankline)
    return _strip_trailing_lf(output)


def _insert_blankline_markers(s: str, marker: str):
    return re.sub(r"(?m)^[ ]*(?=\n)", marker, s)


def _strip_trailing_lf(s: str):
    return s[:-1] if s[-1:] == "\n" else s


def _print_mismatch_reason(reason: Any, test: Test):
    msg = str(reason)
    # Try format spec error message
    m = re.match(r"format spec '(.+?)' not recognized", msg)
    if m:
        type = m.group(1)
        line = _find_parse_type_line(type, test.expected)
        line_msg = f" on line {line}" if line is not None else ""
        print(f"    Unsupported parse type '{type}'{line_msg}")
    else:
        print(f"    {msg}")


def _find_parse_type_line(type: str, s: str):
    m = re.search(rf"{{\s*(?:[^\s:]+)?\s*:\s*{re.escape(type)}\s*?}}", s)
    if m:
        return s[: m.start()].count("\n") + 1
    return None


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
    opts = " ".join(_coerce_list(opts))
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
            log.debug("Using project config in %s", filename)
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
