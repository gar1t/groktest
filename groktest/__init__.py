# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from types import ModuleType

import copy
import difflib
import doctest
import importlib
import inspect
import io
import json
import logging
import os
import re
import sys
import tokenize
from typing import Any, Callable, Generator, Iterator, Sequence, Union, cast

import yaml

from . import _vendor_parse as parselib
from . import _vendor_tomli as toml

__all__ = [
    "__version__",
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
    "Skip",
    "Test",
    "TestMatch",
    "TestMatcher",
    "TestResult",
    "TestSpec",
    "TestTypeNotSupported",
    "decode_options",
    "init_runner_state",
    "match_test_output",
    "matcher",
    "parse_front_matter",
    "parse_match",
    "parse_type",
    "parse_tests",
    "start_runtime",
    "test_file",
]

__version__ = "0.3.2"  # Sync with pyproject.toml

log = logging.getLogger("groktest")


class Skip(RuntimeError):
    def __init__(self):
        super().__init__("skip")


class Panic(Exception):
    pass


class Error(Exception):
    pass


class TestTypeNotSupported(Error):
    pass


class RuntimeNotSupported(Error):
    pass


class ProjectDecodeError(Error):
    pass


ProjectConfig = dict[str, Any]

FrontMatter = dict[str, Any]

TestConfig = dict[str, Any]

TestOptions = dict[str, Any]

ParseTypes = dict[str, str]

ParseTypeFunction = Callable[[str], Any]

ParseTypeFunctions = dict[str, ParseTypeFunction]

TransformFunction = Callable[[str, str], tuple[str, str]]

OptionFunction = Callable[[Any, TestOptions, "Test"], TransformFunction | None]

OptionFunctions = dict[str, OptionFunction]


class TestSummary:
    def __init__(self):
        self.failed: list[Test] = []
        self.tested: list[Test] = []
        self.skipped: list[Test] = []

    def __repr__(self):
        return (
            f"<TestSummary failed={len(self.failed)}"
            f" tested={len(self.tested)}"
            f" skipped={len(self.skipped)}>"
        )


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


class TestProxy(Test):
    def __init__(self, filename: str):
        super().__init__("", "", filename, 0, {})


class TestResult:
    def __init__(self, code: int, output: str, short_error: str | None = None):
        self.code = code
        self.output = output
        self.short_error = short_error


class Runtime:
    def start(self, config: TestConfig | None = None) -> None:
        raise NotImplementedError()

    def init_for_tests(self, config: TestConfig | None = None) -> None:
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
    def __init__(self, runtime: Runtime, stop_timeout: int | None = None):
        self.runtime = runtime
        self.stop_timeout = stop_timeout

    def __enter__(self):
        return self

    def __exit__(self, *exc: Any):
        try:
            _stop_runtime(self.runtime, self.stop_timeout)
        except Exception as e:
            if log.getEffectiveLevel() <= logging.DEBUG:
                log.exception("Stopping runtime")
            log.error("Error stopping runtime: %s", e)


def _stop_runtime(runtime: Runtime, timeout: int | None):
    if timeout is not None:
        runtime.stop(timeout)
    else:
        runtime.stop()


Printer = Callable[[str], None]


class RunnerState:
    def __init__(
        self,
        tests: list[Test],
        runtime: Runtime,
        spec: TestSpec,
        config: TestConfig,
        filename: str,
        print_output: Printer | None = None,
        parse_functions: ParseTypeFunctions | None = None,
        option_functions: OptionFunctions | None = None,
    ):
        self.tests = tests
        self.runtime = runtime
        self.spec = spec
        self.filename = filename
        self.config = config
        self.summary = TestSummary()
        self.skip_rest = False
        self.skip_rest_for_fail_fast = False
        self.print_output = print_output or print
        self.parse_functions = parse_functions or {}
        self.option_functions = option_functions or {}


class DocTestRunnerState:
    def __init__(self, filename: str, config: TestConfig):
        self.filename = filename
        self.config = config
        self.results = TestSummary()


class TestMatch:
    def __init__(
        self,
        match: bool,
        vars: dict[str, Any] | None = None,
        reason: Any | None = None,
    ):
        self.match = match
        self.vars = vars
        self.reason = reason


TestMatcher = Callable[
    [
        str,
        str,
        TestOptions | None,
        RunnerState | None,
    ],
    TestMatch,
]


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
    r"[+]([\w\-]+)(?:\s*=\s*((?:'.*?')|(?:\".*?\")|(?:[^\s]+)))?"  # \
    r"|[-]([\w\-]+)",
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


def _gen_comments(comment_marker: str = "#"):
    def f(s: str):
        # Naively look for comment marker from right
        for line in s.split("\n"):
            parts = line.rsplit("#", 1)
            if len(parts) > 1:
                yield parts[1]

    return f


NUSHELL_SPEC = TestSpec(
    runtime="nushell",
    ps1=">",
    ps2=":::",
    test_pattern=DEFAULT_TEST_PATTERN,
    blankline="⤶",
    wildcard="...",
    option_candidates=_gen_comments("#"),
)

Marker = Any

DOCTEST_MARKER: Marker = object()

SPECS: dict[str, Union[TestSpec, Marker]] = {
    "python": PYTHON_SPEC,
    "nushell": NUSHELL_SPEC,
    "doctest": DOCTEST_MARKER,
}

RUNTIME = {
    "doctest": "groktest.doctest.DoctestRuntime",
    "python": "groktest.python.PythonRuntime",
    "nushell": "groktest.nushell.NuShellRuntime",
}


def init_runner_state(
    filename: str,
    project_config: ProjectConfig | None = None,
    print_output: Printer | None = None,
):
    filename = os.path.abspath(filename)
    contents = _read_file(filename)
    fm = parse_front_matter(contents, filename)
    spec = _spec_for_front_matter(fm, filename)
    test_config = _test_config(fm, project_config, filename)
    log.debug("Test config: %s", test_config)
    if spec is DOCTEST_MARKER:
        return DocTestRunnerState(filename, test_config)
    runtime = start_runtime(spec.runtime, test_config)
    tests = parse_tests(contents, spec, filename)
    return RunnerState(
        tests,
        runtime,
        spec,
        test_config,
        filename,
        print_output or print,
        _parse_type_functions(test_config),
        _option_functions(test_config),
    )


def _read_file(filename: str):
    bytes = open(filename, "rb").read()
    return _norm_line_endings(bytes).decode()


def _norm_line_endings(b: bytes):
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


_FRONT_MATTER_P = re.compile(r"\s*^---\n(.*)\n---\n?$", re.MULTILINE | re.DOTALL)


def parse_front_matter(s: str, filename: str):
    """Parse front matter from string.

    Front matter can be defined using YAML, JSON, or INI.

    If PyYaml is installed, it's used to parse front matter. As this
    library has no external dependencies, if PyYaml is not installed, a
    parsing hack is used in attempt to parse front matter as YAML. In
    this case, front matter configuration is limited to simple key value
    pairs using `<key>: <value>` syntax.
    """
    return cast(
        FrontMatter,
        {
            **_parsed_front_matter(s, filename),
            "__src__": filename,
        },
    )


def _parsed_front_matter(s: str, filename: str):
    m = _FRONT_MATTER_P.match(s)
    if not m:
        log.debug("No front matter for %s", filename)
        return cast(FrontMatter, {})
    s = m.group(1)
    try:
        data = _try_parsers([_parse_json, _parse_toml, _parse_yaml], s, filename)
    except ValueError:
        log.warning(
            "Unable to parse front matter in %s - verify valid JSON, TOML, or YAML",
            filename,
        )
        return cast(FrontMatter, {})
    else:
        if isinstance(data, str):
            log.warning(
                "Unable to parse front matter in %s - verify valid JSON, TOML, or YAML",
                filename,
            )
            return cast(FrontMatter, {})
        if not isinstance(data, dict):
            log.warning(
                "Invalid front matter in %s, expected mapping but got %s",
                filename,
                type(data).__name__,
            )
            return cast(FrontMatter, {})
    return cast(FrontMatter, data)


Parser = Callable[[str, str], FrontMatter]


def _try_parsers(parsers: list[Parser], s: str, filename: str):
    for p in parsers:
        try:
            return p(s, filename)
        except ValueError:
            pass
    raise ValueError()


def _parse_json(s: str, filename: str):
    try:
        return json.loads(s)
    except Exception as e:
        log.debug("Could not parse JSON front matter for %s: %s", filename, e)
        raise ValueError(e) from None


def _parse_toml(s: str, filename: str):
    try:
        return toml.loads(s)
    except toml.TOMLDecodeError as e:
        log.debug("Could not parse TOML front matter for %s: %s", filename, e)
        raise ValueError(e) from None


def _parse_yaml(s: str, filename: str):
    try:
        return yaml.safe_load(s)
    except Exception as e:
        log.debug("Could not parse YAML front matter for %s: %s", filename, e)
        raise ValueError(e) from None


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
        _spec_for_front_matter_test_type(fm, filename)
        or _spec_for_project_default_type(filename)
        or _default_spec_for_missing_or_invalid_front_matter(fm, filename)
        or DEFAULT_SPEC
    )


def _spec_for_front_matter_test_type(fm: dict[str, Any], filename: str):
    if not isinstance(fm, dict):
        return None
    try:
        test_type = fm["tool"]["groktest"]["type"]
    except KeyError:
        test_type = fm.get("test-type")
    if not test_type:
        return None
    return _spec_for_type(test_type)


def _spec_for_type(type: str):
    try:
        return SPECS[type]
    except KeyError:
        raise TestTypeNotSupported(type) from None


def _spec_for_project_default_type(filename: str):
    config = _try_test_file_project_config(filename)
    if not config:
        return None
    try:
        default_type = config["default-type"]
    except KeyError:
        return None
    else:
        return _spec_for_type(default_type)


def _default_spec_for_missing_or_invalid_front_matter(fm: Any, filename: str):
    if not fm:
        return DEFAULT_SPEC
    if not isinstance(fm, dict):
        log.warning(
            "Unexpected front matter type %s in %s, expected map", type(fm), filename
        )
        return DEFAULT_SPEC
    return None


def parse_tests(content: str, spec: TestSpec, filename: str):
    tests = []
    charpos = linepos = 0
    for m in spec.test_pattern.finditer(content):
        linepos += content.count("\n", charpos, m.start())
        tests.append(_test_for_match(m, spec, linepos, filename))
        linepos += content.count('\n', m.start(), m.end())
        charpos = m.end()
    return cast(list[Test], tests)


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


def _strip_prompts(lines: list[str], spec: TestSpec, linepos: int, filename: str):
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
    options: dict[str, Any] = {}
    for part in _test_option_candidates(expr, spec):
        options.update(decode_options(part))
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


def _strip_trailing_empty_line(lines: list[str]):
    if len(lines) and not lines[-1].strip():
        lines.pop()


def _check_test_indent(lines: list[str], indent: int, linepos: int, filename: str):
    prefix = " " * indent
    for i, line in enumerate(lines):
        if line and not line.startswith(prefix):
            raise ValueError(
                f"File \"{filename}\", line {linepos + i + 1}, in test: "
                "inconsistent leading whitespace"
            )


def _test_config(
    test_fm: FrontMatter,
    project_config: ProjectConfig | None,
    filename: str,
):
    project_config = project_config or {}
    if "__src__" not in project_config:
        project_config.update(_try_test_file_project_config(filename) or {})
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
    src = fm.get("__src__")
    try:
        config = fm["tool"]["groktest"]
    except KeyError:
        config = _mapped_front_matter_config(fm)
    return {**config, **({"__src__": src} if src else {})}


FRONT_MATTER_TO_CONFIG = {
    "parse-types": ["parse", "types"],
    "parse-functions": ["parse", "functions"],
    "option-functions": ["option", "functions"],
    "python-init": ["python", "init"],
    "test-options": ["options"],
    "nushell-init": ["nushell", "init"],
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


def _merge_kv_dest(
    path: list[str],
    src: dict[str, Any],
    dest: dict[str, Any],
) -> Union[tuple[None, None, None], tuple[str, Any, dict[str, Any]]]:
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


def _merge_append_list(path: list[str], src: dict[str, Any], dest: dict[str, Any]):
    key, src_val, append_dest = _merge_kv_dest(path, src, dest)
    if not key:
        return
    assert append_dest
    append_dest[key] = _coerce_list(src_val) + _coerce_list(append_dest.get(key))


def _merge_items(path: list[str], src: dict[str, Any], dest: dict[str, Any]):
    key, src_val, merge_dest = _merge_kv_dest(path, src, dest)
    if not key:
        return
    assert merge_dest
    merge_dest.setdefault(key, {}).update(src_val)


def _coerce_list(x: Any) -> list[Any]:
    return x if isinstance(x, list) else [] if x is None else [x]


def _try_test_file_project_config(filename: str):
    for dirname in _iter_parents(filename):
        paths = [
            os.path.join(dirname, "pyproject.toml"),
        ]
        for path in paths:
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


def start_runtime(name: str, config: TestConfig | None = None):
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


def _parse_type_functions(config: TestConfig) -> ParseTypeFunctions:
    return {
        **_module_parse_type_functions(config),
        **_regex_parse_type_functions(config),
    }


def _module_parse_type_functions(config: TestConfig) -> ParseTypeFunctions:
    try:
        spec = config["parse"]["functions"]
    except KeyError:
        return {}
    else:
        spec = _coerce_list(spec)
        module_path = _config_src_path(config)
        return dict(_iter_named_functions(spec, module_path, "parse_", "type_name"))


def _config_src_path(config: TestConfig):
    config_src: list[str] = _coerce_list(config["__src__"])
    return [os.path.dirname(path) for path in config_src]


def _iter_named_functions(
    modules: list[Any],
    module_path: list[str],
    function_prefix: str,
    name_attr: str,
) -> Generator[tuple[str, Callable[..., Any]], None, None]:
    for module_name in modules:
        log.debug("Loading parse functions from %s", module_name)
        module = _try_load_module(module_name, module_path)
        if not module:
            continue
        for f in _iter_module_functions(module, function_prefix):
            function_name = _function_name(f, name_attr, function_prefix)
            log.debug("Registering function %s as '%s' type", f.__name__, function_name)
            yield function_name, f


def _try_load_module(spec: str, path: list[str]):
    if not isinstance(spec, str):
        log.warning("Invalid value for functions %r, expected a string", spec)
        return None
    _ensure_sys_path_for_doc_tests(path)
    try:
        return importlib.import_module(spec)
    except Exception as e:
        if log.getEffectiveLevel() <= logging.DEBUG:
            log.exception("Loading module %r", spec)
        else:
            log.warning("Error loading functions from %r: %r", spec, e)
        return None


def _ensure_sys_path_for_doc_tests(doctest_path: list[str]):
    # Add in reverse order as doctest path goes from more specific (test
    # file path) to less specific (project path)
    for p in reversed(doctest_path):
        if p not in sys.path:
            sys.path.append(p)


def _function_name(f: Callable[[str], Any], name_attr: str, prefix: str):
    try:
        return getattr(f, name_attr)
    except AttributeError:
        name = f.__name__
        assert name.startswith(prefix)
        return name[len(prefix) :]


def _iter_module_functions(
    module: ModuleType,
    function_prefix: str,
) -> Generator[ParseTypeFunction, None, None]:
    for name in _exported_names(module, function_prefix):
        x = getattr(module, name)
        if _is_function(x):
            yield x


def _exported_names(module: ModuleType, prefix: str):
    all = getattr(module, "__all__", [])
    if isinstance(all, str):
        all = all.split()
    return [name for name in (all or dir(module)) if name.startswith(prefix)]


def _is_function(x: Any):
    # Simple sniff-test for callable with at least one arg
    try:
        sig = inspect.signature(x)
    except TypeError:
        return False
    else:
        return len(sig.parameters) >= 1


def _regex_parse_type_functions(config: TestConfig) -> ParseTypeFunctions:
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

    f.pattern = pattern  # type: ignore
    return f


def _option_functions(config: TestConfig) -> OptionFunctions:
    try:
        spec = config["option"]["functions"]
    except KeyError:
        return {}
    else:
        spec = _coerce_list(spec)
        module_path = _config_src_path(config)
        return dict(_iter_named_functions(spec, module_path, "option_", "option_name"))


def test_file(
    filename: str,
    config: ProjectConfig | None = None,
    print_output: Printer | None = None,
):
    state = init_runner_state(filename, config, print_output)
    if isinstance(state, DocTestRunnerState):
        _doctest_file(state)
        return state.results
    assert isinstance(state, RunnerState)
    assert state.runtime.is_available
    state.runtime.init_for_tests(state.config)
    _apply_skip_for_solo(state.tests)
    with RuntimeScope(state.runtime):
        for test in state.tests:
            if state.skip_rest_for_fail_fast:
                _handle_test_skipped(test, state)
            else:
                test_options = _test_options(test, state)
                _apply_skip_rest(test_options, state)
                if _skip_test(test, test_options, state):
                    _handle_test_skipped(test, state)
                else:
                    run_test(test, test_options, state)
        return state.summary


def run_test(test: Test, options: TestOptions, state: RunnerState):
    try:
        result = state.runtime.exec_test_expr(test, options)
    except Exception as e:
        if log.getEffectiveLevel() <= logging.DEBUG:
            log.exception("")
        log.error(
            "Unhandled error running test at %s:%s: %s", test.filename, test.line, e
        )
        raise Panic()
    _handle_test_result(result, test, options, state)


def _apply_skip_for_solo(tests: list[Test]):
    solo_tests = [test for test in tests if test.options.get("solo")]
    if not solo_tests:
        return
    for test in tests:
        test.options["skip"] = test not in solo_tests


def _apply_skip_rest(options: TestOptions, state: RunnerState):
    state.skip_rest = _option_value("skiprest", options, state.skip_rest)


def _skip_test(test: Test, options: TestOptions, state: RunnerState):
    val = _option_value("skip", options, None)
    if val is None:
        val = _try_option_function_skip(test, options, state)
    elif isinstance(val, str):
        if val[:1] == "!":
            val = not bool(os.getenv(val[1:]))
        else:
            val = bool(os.getenv(val))
    return val if val is not None else state.skip_rest


def _try_option_function_skip(test: Test, options: TestOptions, state: RunnerState):
    for name, f in state.option_functions.items():
        val = options.get(name)
        if val is None:
            continue
        try:
            _apply_option_args(f, val, options, test)
        except Skip:
            return True
        except Exception as e:
            if e.args == ("skip",):
                return True
            if log.getEffectiveLevel() <= logging.DEBUG:
                log.exception(name)
            log.warning(
                "Error evaluating option '%s' at %s:%i: %s",
                name,
                test.filename,
                test.line,
                e,
            )
    return None


def _apply_option_args(f: Callable[..., Any], *args: Any):
    f_arg_count = len(inspect.signature(f).parameters)
    return f(*args[:f_arg_count])


def _handle_test_skipped(test: Test, state: RunnerState):
    state.summary.skipped.append(test)


def _handle_test_result(
    result: TestResult,
    test: Test,
    options: TestOptions,
    state: RunnerState,
):
    expected = _format_match_expected(test, options, state)
    output_candidates = _match_test_output_candidates(result, test, options, state)
    match, match_output = _try_match_output_candidates(
        output_candidates, expected, test, state
    )
    _log_test_result_match(match, result, test, expected, match_output, state)
    if options.get("fails"):
        if match.match:
            _handle_unexpected_test_pass(test, options, state)
        else:
            _handle_expected_test_failed(test, options, state)
    elif match.match:
        _handle_test_passed(test, match, state)
    else:
        _handle_test_failed(test, match, result, options, state)


def _log_test_result_match(
    match: TestMatch,
    result: TestResult,
    test: Test,
    used_expected: str,
    used_test_output: str,
    state: RunnerState,
):
    log.debug("Result for %r", test.expr)
    log.debug("  match:           %s", "yes" if match.match else "no")
    if match.match:
        log.debug("  match vars:    %s", match.vars)
    log.debug("  test expected:   %r", test.expected)
    log.debug("  test output [%r]: %r", result.code, result.output)
    log.debug("  used expected:   %r", used_expected)
    log.debug("  used output:     %r", used_test_output)


def _try_match_output_candidates(
    output_candidates: list[str],
    expected: str,
    test: Test,
    state: RunnerState,
):
    assert output_candidates
    match = None
    matched_output = None
    for output in output_candidates:
        match = match_test_output(expected, output, test, state)
        matched_output = output
        if match.match:
            break
    assert match
    assert matched_output is not None
    return match, matched_output


def _handle_unexpected_test_pass(test: Test, options: TestOptions, state: RunnerState):
    _print_failed_test_sep(options, state)
    state.print_output(f"File \"{test.filename}\", line {test.line}")
    state.print_output("Failed example:")
    _print_test_expr(test.expr, state)
    state.print_output("Expected test to fail but passed")
    state.summary.failed.append(test)
    state.summary.tested.append(test)


def _handle_expected_test_failed(test: Test, options: TestOptions, state: RunnerState):
    # This case is not a failure - it's expected
    state.summary.tested.append(test)


def _format_match_expected(test: Test, options: TestOptions, state: RunnerState):
    expected = _append_lf_for_non_empty(test.expected)
    expected = _maybe_remove_blankline_markers(expected, options, state.spec)
    expected = _maybe_normalize_whitespace(expected, options)
    expected = _maybe_normalize_paths(expected, options)
    expected = _apply_option_functions(expected, test, options, state)
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


def _apply_option_functions(
    s: str,
    test: Test,
    options: TestOptions,
    state: RunnerState,
):
    for name, f in state.option_functions.items():
        val = options.get(name)
        if val is None:
            continue
        f = _apply_option_args_no_raise(f, val, options, test)
        if not f:
            continue
        log.debug("Applying option '%s' to string:\n%s", name, s)
        try:
            s = f(s)
        except Exception as e:
            if log.getEffectiveLevel() <= logging.DEBUG:
                log.exception(name)
            log.warning(
                "Error evaluating option '%s' at %s:%i: %s",
                name,
                test.filename,
                test.line,
                e,
            )
        else:
            log.debug("After option '%s':\n%s", name, s)

    return s


def _apply_option_args_no_raise(f: Callable[..., Any], *args: Any):
    f_arg_count = len(inspect.signature(f).parameters)
    try:
        return f(*args[:f_arg_count])
    except Exception:
        log.exception(str([f, *args]))
        return None


def _match_test_output_candidates(
    result: TestResult,
    test: Test,
    options: TestOptions,
    state: RunnerState,
):
    output = _format_test_output(result.output, test, options, state)
    short_error = _maybe_short_error(result, options)
    if short_error:
        return [output, _format_test_output(short_error, test, options, state)]
    return [output]


def _format_test_output(
    output: str,
    test: Test,
    options: TestOptions,
    state: RunnerState,
):
    output = _truncate_empty_line_spaces(output)
    output = _maybe_normalize_whitespace(output, options)
    output = _maybe_normalize_paths(output, options)
    output = _apply_option_functions(output, test, options, state)
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
    state: RunnerState,
):
    test_options = _test_options(test, state)
    return matcher(test_options)(expected, test_output, test_options, state)


def _test_options(test: Test, state: RunnerState):
    options = {
        **_test_options_for_config(state.config, test.filename),
        **test.options,
    }
    _maybe_apply_spec_wildcard(state.spec, options)
    return cast(TestOptions, options)


def _test_options_for_config(config: TestConfig, filename: str):
    options = config.get("options")
    if not options:
        return cast(TestOptions, {})
    parsed: TestOptions = {}
    # Visible options in reverse order as left-most takes priority
    for part in reversed(_coerce_list(options)):
        if not isinstance(part, str):
            log.warning("Invalid option %r in %s: expected string", part, filename)
            continue
        parsed.update(decode_options(part))
    return parsed


def decode_options(s: str) -> dict[str, Any]:
    return dict(_name_val_for_option_match(m) for m in OPTIONS_PATTERN.finditer(s))


def _name_val_for_option_match(m: re.Match[str]) -> tuple[str, Any]:
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
    options: TestOptions | None = None,
    state: RunnerState | None = None,
):
    options = options or {}
    case_sensitive = _option_value("case", options, True)
    extra_types = state.parse_functions if state else {}
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


def _option_value(name: str, options: dict[str, Any], default: Any):
    try:
        val = options[name]
    except KeyError:
        return default
    else:
        if val is None:
            return default
        return val


def str_match(
    expected: str,
    test_output: str,
    options: TestOptions | None = None,
    state: RunnerState | None = None,
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
    options: TestOptions | None,
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
    options: TestOptions | None = None,
):
    return TestMatch(True) if test_output == expected else TestMatch(False)


def _handle_test_passed(test: Test, match: TestMatch, state: RunnerState):
    state.runtime.handle_test_match(match)
    state.summary.tested.append(test)


def _handle_test_failed(
    test: Test,
    match: TestMatch,
    result: TestResult,
    options: TestOptions,
    state: RunnerState,
):
    _print_failed_test_sep(options, state)
    _print_failed_test(test, match, result, options, state)
    state.summary.failed.append(test)
    state.summary.tested.append(test)
    if state.config.get("fail-fast"):
        state.skip_rest_for_fail_fast = True


def _print_failed_test_sep(options: TestOptions, state: RunnerState):
    sep = _option_value("sep", options, True)
    if sep is True:
        state.print_output("*" * 70)
    elif sep:
        state.print_output(sep)


def _print_failed_test(
    test: Test,
    match: TestMatch,
    result: TestResult,
    options: TestOptions,
    state: RunnerState,
):
    state.print_output(f"File \"{test.filename}\", line {test.line}")
    state.print_output("Failed example:")
    _print_test_expr(test.expr, state)
    if test.expected and options.get("diff"):
        _print_test_result_diff(test, result, options, state)
    else:
        _print_test_expected(test, state)
        _print_test_result_output(result, options, state)
    if match.reason:
        state.print_output("Reason:")
        _print_mismatch_reason(match.reason, test, state)


def _print_test_expr(expr: str, state: RunnerState):
    expr = expr.strip()
    for line in expr.split("\n"):
        state.print_output("    " + line)


def _print_test_result_diff(
    test: Test,
    result: TestResult,
    options: TestOptions,
    state: RunnerState,
):
    expected_lines, output_lines = _format_lines_for_diff(
        test, result, options, state.spec
    )
    state.print_output("Differences between expected and actual:")
    for line in _diff_lines(expected_lines, output_lines):
        state.print_output("   " + line)


def _format_lines_for_diff(
    test: Test, result: TestResult, options: TestOptions, spec: TestSpec
):
    expected = test.expected
    output = _format_test_result_output(result.output, options, spec)
    return (expected.split("\n"), output.split("\n"))


def _diff_lines(a: list[str], b: list[str]):
    diff = difflib.unified_diff(a, b, n=2)
    diff_no_header = list(diff)[2:]
    for line in diff_no_header:
        yield line.rstrip()


def _print_test_expected(test: Test, state: RunnerState):
    if test.expected:
        state.print_output("Expected:")
        expected = _format_test_result_expected(test.expected)
        for line in expected.split("\n"):
            state.print_output("    " + line)
    else:
        state.print_output("Expected nothing")


def _format_test_result_expected(expected: str):
    return expected.strip()


def _print_test_result_output(
    result: TestResult,
    options: TestOptions,
    state: RunnerState,
):
    if result.output:
        state.print_output("Got:")
        output = _format_test_result_output(result.output, options, state.spec)
        for line in output.split("\n"):
            state.print_output("    " + line)
    else:
        state.print_output("Got nothing")


def _format_test_result_output(output: str, options: TestOptions, spec: TestSpec):
    blankline = _blankline_marker(options, spec)
    if blankline:
        output = _insert_blankline_markers(output, blankline)
    return _strip_trailing_lf(output)


def _insert_blankline_markers(s: str, marker: str):
    return re.sub(r"(?m)^[ ]*(?=\n)", marker, s)


def _strip_trailing_lf(s: str):
    return s[:-1] if s[-1:] == "\n" else s


def _print_mismatch_reason(reason: Any, test: Test, state: RunnerState):
    msg = str(reason)
    # Try format spec error message
    m = re.match(r"format spec '(.+?)' not recognized", msg)
    if m:
        type = m.group(1)
        line = _find_parse_type_line(type, test.expected)
        line_msg = f" on line {line}" if line is not None else ""
        state.print_output(f"    Unsupported parse type '{type}'{line_msg}")
    else:
        state.print_output(f"    {msg}")


def _find_parse_type_line(type: str, s: str):
    m = re.search(rf"{{\s*(?:[^\s:]+)?\s*:\s*{re.escape(type)}\s*?}}", s)
    if m:
        return s[: m.start()].count("\n") + 1
    return None


def _doctest_file(state: DocTestRunnerState):
    failed, tested = doctest.testfile(
        state.filename,
        module_relative=False,
        optionflags=_doctest_options(state.config),
    )
    test = TestProxy(state.filename)
    if failed:
        assert tested, state.filename
        state.results.failed.append(test)
    if tested:
        state.results.tested.append(test)


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


def _iter_doctest_opts(opts: str) -> Generator[tuple[int, bool], None, None]:
    import doctest

    for opt in re.findall(r"(?i)[+-][a-z0-9_]+", opts):
        assert opt[0] in ("+", "-"), (opt, opts)
        enabled, opt = opt[0] == "+", opt[1:]
        try:
            yield getattr(doctest, opt.upper()), enabled
        except AttributeError:
            pass


def load_project_config(filename: str):
    try:
        data = _load_toml(filename)
    except toml.TOMLDecodeError as e:
        raise ProjectDecodeError(e, filename) from None
    else:
        return _project_config_for_data(data)


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
            if not isinstance(data, dict):
                raise SystemExit(
                    f"Unexpected config in {filename}: expected "
                    f"mapping but got {type(data).__name__}"
                )
            data["__src__"] = filename
            return data


def _project_config_for_data(data: dict[str, Any]):
    try:
        groktest_data = data["tool"]["groktest"]
    except KeyError:
        return cast(ProjectConfig, {})
    else:
        groktest_data["__src__"] = data["__src__"]
        return cast(ProjectConfig, groktest_data)


def parse_type(name: str, pattern: str, group_count: int = 0):
    def decorator(f: Callable[[str], Any]):
        f.type_name = name  # type: ignore
        f.pattern = pattern  # type: ignore
        f.regex_group_count = group_count  # type: ignore
        return f

    return decorator
