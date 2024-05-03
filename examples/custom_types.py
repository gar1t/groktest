import re

__all__ = ["parse_ver", "parse_upper", "option_skip_red"]

# See https://github.com/r1chardj0n3s/parse#custom-type-conversions

_VER_PATTERN = r"(\d+).(\d+).(\d+)"


def parse_ver(s: str):
    m = re.match(_VER_PATTERN, s)
    if m:
        return tuple(map(int, m.groups()))
    return None


parse_ver.pattern = _VER_PATTERN
parse_ver.regex_group_count = 3


def parse_upper(s: str):
    return s.upper()


# Groktest specific attr `type_name` to configure name
parse_upper.type_name = "loud"


# Not available to tests as it's not defined in `__all__`
def parse_internal(s: str):
    return s


def option_skip_red(val: str):
    return val == "red"


option_skip_red.option_name = "skip-red"
