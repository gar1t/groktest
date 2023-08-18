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
    def __init__(self, name: str, runtime: str, test_pattern: Pattern[str]):
        self.name = name
        self.runtime = runtime
        self.test_pattern = test_pattern

    def __str__(self):
        return f"<groktest.Config '{self.name}'>"


class TestSource:
    def __init__(self, filename: str, line: int):
        self.filename = filename
        self.line = line


class Test:
    def __init__(
        self,
        expr: str,
        expected: str,
        source: TestSource,
        config: Config,
    ):
        self.expr = expr
        self.expected = expected
        self.source = source
        self.config = config


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
    test_pattern=re.compile(r""),
)

CONFIG: Dict[str, Config] = {"python": PYTHON_CONFIG}

RUNTIME = {"python": PythonRuntime()}


def init_runner_state(filename: str):
    contents = _read_file(filename)
    fm = _parse_front_matter(contents, filename)
    config = _config_for_front_matter(fm, filename)
    runtime = _runtime_for_config(config)
    tests = parse_tests(contents, config)
    return RunnerState(tests, runtime)


def _read_file(filename: str):
    return open(filename).read()


_FRONT_MATTER_P = re.compile(r"\s*^---\n(.*)\n---\n?$", re.MULTILINE | re.DOTALL)


def _parse_front_matter(s: str, ref: str) -> Any:
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
        _try_parse_full_yaml(fm, ref)
        or _try_parse_json(fm, ref)
        or _try_parse_ini(fm, ref)
        or _try_parse_simple_yaml(fm, ref)
        or {}
    )


def _try_parse_full_yaml(s: str, ref: str, raise_error: bool = False):
    try:
        import yaml  # type: ignore
    except ImportError:
        if raise_error:
            raise
        log.debug("yaml module not available, skipping full YAML for %s", ref)
        return None
    try:
        return yaml.safe_load(s)
    except Exception as e:
        if raise_error:
            raise
        log.debug("ERROR parsing YAML for %s: %s", ref, e)
        return None


def _try_parse_json(s: str, ref: str, raise_error: bool = False):
    try:
        return json.loads(s)
    except Exception as e:
        if raise_error:
            raise
        log.debug("ERROR parsing JSON for %s: %s", ref, e)
        return None


def _try_parse_ini(
    s: str, ref: str, raise_error: bool = False
) -> Optional[Dict[str, Any]]:
    parser = configparser.ConfigParser()
    try:
        parser.read_string("[__anonymous__]\n" + s)
    except configparser.Error as e:
        if raise_error:
            raise
        log.debug("ERROR parsing INI for %s: %s", ref, e)
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
    if s[:1] + s[-1:] in ('""', "''"):
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


def _try_parse_simple_yaml(s: str, ref: str, raise_error: bool = False):
    # INI format resembles YAML when ':' key/val delimiter is used
    return _try_parse_ini(s, ref, raise_error)


def _config_for_front_matter(fm: Any, ref: str):
    return (
        _default_config_for_missing_or_invalid_front_matter(fm, ref)
        or _config_for_test_type(fm, ref)
        or _explicit_config(fm, ref)
        or DEFAULT_CONFIG
    )


def _default_config_for_missing_or_invalid_front_matter(fm: Any, ref: str):
    if not fm:
        return DEFAULT_CONFIG
    if not isinstance(fm, dict):
        log.warning(
            "Unexpected front matter type %s in %s, expected map", type(fm), ref
        )
        return DEFAULT_CONFIG
    return None


def _config_for_test_type(fm: Dict[str, Any], ref: str):
    assert isinstance(fm, dict)
    test_type = fm.get("test-type")
    if not test_type:
        return None
    try:
        return CONFIG[test_type]
    except KeyError:
        raise TestTypeNotSupported(test_type)


def _explicit_config(fm: Any, ref: str):
    assert isinstance(fm, dict)
    config = fm.get("test-config")
    if not config:
        return None
    assert False, ("TODO", config)


def parse_tests(content: str, config: Config):
    for part in config.test_pattern.finditer(content):
        print(part)
    return cast(List[Test], [])


def _runtime_for_config(config: Config):
    try:
        return RUNTIME[config.runtime]
    except KeyError:
        raise RuntimeNotSupported(config.runtime)


def test_file(filename: str):
    """
    - Load the file

    - Parse it into a list of str and tests

      - Do we need the non-example parts? doctest keeps it for
        'script_to_example' - for now let's keep it and an iterator to
        pull tests out

    """
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

    options = doctest.ELLIPSIS
    return doctest.testfile(filename, module_relative=False, optionflags=options)


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
