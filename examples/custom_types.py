import re
from typing import Any

__all__ = [
    "parse_ver",
    "parse_upper",
    "option_skip_red",
    "option_table",
]

# See https://github.com/r1chardj0n3s/parse#custom-type-conversions

_VER_PATTERN = r"(\d+).(\d+).(\d+)"


def parse_ver(s: str):
    m = re.match(_VER_PATTERN, s)
    if m:
        return tuple(map(int, m.groups()))
    return None


parse_ver.pattern = _VER_PATTERN  # type: ignore
parse_ver.regex_group_count = 3  # type: ignore


def parse_upper(s: str):
    return s.upper()


# Groktest specific attr `type_name` to configure name
parse_upper.type_name = "loud"  # type: ignore


# Not available to tests as it's not defined in `__all__`
def parse_internal(s: str):
    return s


def option_skip_red(val: Any):
    if val == "red":
        raise RuntimeError("skip")


option_skip_red.option_name = "skip-red"  # type: ignore


def option_table(val: Any):
    if True:
        return _strip_table


def _strip_table(s: str):
    p1 = re.compile(r" +\|")
    p2 = re.compile(r"-+\|")
    return "\n".join([p2.sub("-|", p1.sub(" |", line)) for line in s.split("\n")])
