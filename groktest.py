# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import *

import json
import configparser
import logging
import os
import re

log = logging.getLogger("groktest")


class Error(Exception):
    pass


class TestTypeNotSupported(Error):
    pass


class RuntimeNotSupported(Error):
    pass


class Config:
    def __init__(self, name: str, runtime: str, ps1: str, ps2: str, test_pattern: str):
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


class Runtime:
    def apply_test(self, test: Test, state: RunnerState):
        raise NotImplemented()


class PythonRuntime(Runtime):
    pass


class RunnerState:
    def __init__(self, tests: List[Test], runtime: Runtime):
        self.tests = tests
        self.runtime = runtime
        self.results: Dict[str, Any] = {"failed": 0, "tested": 0}


PYTHON_CONFIG = DEFAULT_CONFIG = Config(
    name="python",
    runtime="python",
    ps1=">>>",
    ps2="...",
    test_pattern=r"""
        # Credit: Tim Peters, et al. doctest.py
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
    """,
)

CONFIG: Dict[str, Config] = {"python": PYTHON_CONFIG}

RUNTIME = {"python": PythonRuntime()}


def init_runner_state(filename: str):
    contents = _read_file(filename)
    fm = _parse_front_matter(contents, filename)
    config = _config_for_front_matter(fm, filename)
    runtime = _runtime_for_config(config)
    tests = parse_tests(contents, config, filename)
    return RunnerState(tests, runtime)


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
    return s[prompt_len + 1:]


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


def _runtime_for_config(config: Config):
    try:
        return RUNTIME[config.runtime]
    except KeyError:
        raise RuntimeNotSupported(config.runtime)


def test_file(filename: str):
    result = _maybe_doctest_bootstrap(filename)
    if result is not None:
        return result

    state = init_runner_state(filename)
    for test in state.tests:
        state.runtime.apply_test(test, state)
    return state.results


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


def _main_init_logging(args: Any):
    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(levelname)s: [%(name)s] %(message)s",
        )


def _main_test_filenames(args: Any):
    if args.last:
        last = _main_last()
        if not last:
            raise SystemExit(
                "last not found - run at least one test before using '--last'"
            )
        return last
    return args.paths


def _main_last():
    try:
        f = open(_main_last_savefile())
    except FileNotFoundError:
        return None
    else:
        with f:
            return json.load(f)


def _main_save_last(filenames: List[str]):
    with open(_main_last_savefile(), "w") as f:
        json.dump(filenames, f)


def _main_last_savefile():
    import tempfile

    return os.path.join(tempfile.gettempdir(), "groktest.last")


def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument(
        "paths",
        metavar="PATH",
        type=str,
        help="file to test",
        nargs="*",
    )
    p.add_argument("--last", action="store_true", help="re-run last tests")
    p.add_argument("--debug", action="store_true", help="show debug info")
    args = p.parse_args()
    _main_init_logging(args)

    failed = tested = 0

    to_run = _main_test_filenames(args)
    _main_save_last(to_run)

    for filename in to_run:
        print(f"Testing {filename}")
        result = test_file(filename)
        failed += result["failed"]
        tested += result["tested"]

    assert failed <= tested, (failed, tested)
    if tested == 0:
        print("Nothing tested")
    elif failed == 0:
        print("All tests passed 🔥")
    else:
        print("Tests failed - see above for details")


if __name__ == "__main__":
    main()
