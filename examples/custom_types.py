import re

__all__ = ["parse_ver", "parse_upper"]

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


# Not available to tests as it's not defined in `__all__`
def parse_internal(s: str):
    return s
