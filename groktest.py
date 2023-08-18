# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import *

import json
import configparser
import logging
import re

log = logging.getLogger("groktest")

PARSERS: Dict[str, Parser] = {}


class Error(Exception):
    pass


class FormatNotSupported(Error):
    pass


class Config:
    pass


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


PatternType = Union[Literal["test"], Literal["ignore"], Literal["error"]]


class Parser:
    def __init__(self, patterns: Dict[PatternType, Pattern[str]]):
        self.patterns = patterns


class Runtime:
    pass


class PythonRuntime(Runtime):
    pass


class PosixShellRuntime(Runtime):
    pass


class RunnerState:
    def __init__(self):
        pass


def init_runner_state(filename: str):
    contents = _read_file(filename)
    fm = _parse_front_matter(contents, filename)
    config = _config_for_front_matter(fm, filename)
    parser = _parser_for_config(config)
    runtime = _runtime_for_config(config)


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


def _try_parse_simple_yaml(s: str, ref: str, raise_error: bool = False):
    # INI format resembles YAML when ':' key/val delimiter is used
    return _try_parse_ini(s, ref, raise_error)


def _config_for_front_matter(fm: Any, ref: str):
    assert False


def _parser_for_config(config: Config):
    return _parser_for_front_config(config) or _default_parser()


def _parser_for_front_config(config: Config):
    assert False, config


def _parser_for_test_format(format: Any):
    if not format:
        return None
    try:
        return PARSERS[format]
    except KeyError:
        raise FormatNotSupported(format)


def _configured_parser(config: Config):
    # TODO: construct parser from config - e.g. `test-example-pattern`,
    # etc.
    return None


def _default_parser():
    return _parser_for_test_format("groktest")


def _runtime_for_config(config: Config):
    pass


class Runner:
    pass


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
    print(f"TODO test {filename}")
    return 0, 0


def _maybe_doctest_bootstrap(filename: str):
    contents = _read_file(filename)
    fm = _parse_front_matter(contents, filename)
    if fm.get("test-format") == "doctest":
        return _doctest_file(filename)
    return None


def _doctest_file(filename: str):
    import doctest

    options = doctest.ELLIPSIS
    return doctest.testfile(filename, module_relative=False, optionflags=options)


def _init_logging(args: Any):
    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(levelname)s: [%(name)s] %(message)s",
        )


def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument(
        "paths",
        metavar="PATH",
        type=str,
        help="File to test.",
        nargs="+",
    )
    p.add_argument(
        "-f",
        "--format",
        metavar="FORMAT",
        help="Format to use for specified tests.",
    )
    p.add_argument("--debug", action="store_true", help="Print debug info")
    args = p.parse_args()
    _init_logging(args)

    failed = tested = 0

    for filename in args.paths:
        f, t = test_file(filename)
        failed += f
        tested += t

    assert failed <= tested, (failed, tested)
    if tested == 0:
        print("Nothing tested")
    elif failed == 0:
        print("All tests passed 🔥")
    else:
        print("Tests failed - see above for details")


if __name__ == "__main__":
    main()
