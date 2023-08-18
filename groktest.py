# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import *

import json
import configparser
import logging
import re

log = logging.getLogger()

PARSERS: Dict[str, Parser] = {}


class Error(Exception):
    pass


class FormatNotSupported(Error):
    pass


TestConfig = Dict[str, Union[str, int, float]]


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
        config: TestConfig,
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
    config = _parse_front_matter(contents)
    parser = _parser_for_config(config)
    runtime = _runtime_for_config(config)


def _read_file(filename: str):
    return open(filename).read()


_FRONT_MATTER_P = re.compile(r"^---\n(.*?)\n---\n")


def _parse_front_matter(s: str):
    """Parse front matter from string,

    Return a dict of key values with keys starting with  `test-` and
    `gkt-` from string font-matter. Front matter may be specified as
    JSON, INI/TOML or YAML. YAML parsing is simplistic and only supports
    single assignment of string and numbers, which is sufficient for
    config.

    If a key starts with `gkt-` the prefix is normalized to be `test-`.
    This lets users use the `gkt-` prefix to avoid incidental collisions
    with `test-` keys.

    Current implementation is to look for front matter starting from
    line 1, which must be `---\n` to a following line `---\n`. This is a
    convention used for markdown files and should be used for other test
    formats including restructured text.
    """
    m = _FRONT_MATTER_P.match(s)
    if not m:
        return cast(TestConfig, {})
    fm = m.group(1)
    config: TestConfig = (
        _try_parse_json_front_matter(fm)
        or _try_parse_ini_front_matter(fm)
        or _try_parse_yaml_front_matter(fm)
        or {}
    )
    return _normalize_config(config)


def _normalize_config(config: TestConfig) -> TestConfig:
    return {
        _norm_test_option_key(key): config[key]
        for key in config
        if _is_test_option(key)
    }


def _is_key_option(key: str):
    return key.startswith("test-") or key.startswith("gkt-")


def _norm_test_option_key(key: str):
    return f"test-{key[4:]}" if key.startswith("gkt-") else key


def _is_test_option(key: str):
    return key.startswith("test-") or key.startswith("gkt-")


def _try_parse_json_front_matter(s: str):
    try:
        config = json.loads(s)
    except ValueError:
        return None
    else:
        return _validated_front_matter(config)


def _validated_front_matter(config: Any) -> Optional[TestConfig]:
    if not isinstance(config, dict):
        log.warning(f"Unsupported front-matter type ({type(config)}), expected mapping")
        return None
    validated = {}
    for key, val in config.items():
        if not isinstance(val, (int, float, str)):
            if _is_test_option(key):
                log.warning(
                    f"Unsupported test option type ({type(val)}) for {key}, "
                    "expected a string or number"
                )
            continue
        validated[key] = val
    return validated


def _try_parse_ini_front_matter(s: str):
    p = configparser.ConfigParser()
    try:
        p.read_string("[__gk__]\n" + s)
    except configparser.Error:
        return None
    else:
        return _validated_front_matter(dict(p["__gk__"]))


def _try_parse_yaml_front_matter(s: str) -> TestConfig:
    return {
        key: val
        for key, val in (_split_softparse_yaml_line(line) for line in s.split("\n"))
        if _is_key_option(key)
    }


def _split_softparse_yaml_line(line: str):
    parts = line.split(":", 2)
    return _decode_softparse_yaml_kv(*parts) if len(parts) == 2 else ("", parts[0])


def _decode_softparse_yaml_kv(key: str, val: str):
    if _quoted(val):
        return key, val[1:-1]
    try:
        return key, _float_or_int(val)
    except:
        return key, val


def _quoted(s: str):
    return s[:1] + s[-1:] in ('""', "''")


def _float_or_int(val: str):
    try:
        return int(val)
    except ValueError:
        return float(val)


def _parser_for_config(config: TestConfig):
    return _parser_for_front_config(config) or _default_parser()


def _parser_for_front_config(config: TestConfig):
    return _parser_for_test_format(config.get("test-format")) or _configured_parser(
        config
    )


def _parser_for_test_format(format: Any):
    if not format:
        return None
    try:
        return PARSERS[format]
    except KeyError:
        raise FormatNotSupported(format)


def _configured_parser(config: TestConfig):
    # TODO: construct parser from config - e.g. `test-example-pattern`,
    # etc.
    return None


def _default_parser():
    return _parser_for_test_format("groktest")


def _runtime_for_config(config: TestConfig):
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
    state = init_runner_state(filename)

    print(f"TODO test {filename}")


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
    args = p.parse_args()
    for filename in args.paths:
        test_file(filename)


if __name__ == "__main__":
    main()
