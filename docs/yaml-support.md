---
test-type: doctest
---

# Full YAML support

Groktest supports YAML based front matter configuration if PyYAML is
installed. Otherwise Groktest supports a simplistic version of YAML with
only top-level, single line key value assignments.

PyYAML must be installed.

    >>> import yaml

    >>> yaml.__version__  # doctest: +ELLIPSIS
    '6...'

Full YAML front matter parsing is provided by the Groktest function
`_try_parse_full_yaml`.

    >>> import groktest

    >>> def fm(s: str):
    ...     # Raise error for diagnostics
    ...     return groktest._try_parse_full_yaml(s, "<test>", raise_error=True)

For core front matter parsing tests, see [tests.md](tests.md).

Examples:

    >>> fm("")

    >>> from pprint import pprint

    >>> pprint(fm("""
    ... i: 123
    ... f: 123.0
    ... b: yes
    ... m:
    ...   i: 456
    ... l1: [1, 2.0, abc, {def: 789}]
    ... l2:
    ...  - 1
    ...  - 2.0
    ...  - abc
    ...  - def: 789
    ... """))
    {'b': True,
     'f': 123.0,
     'i': 123,
     'l1': [1, 2.0, 'abc', {'def': 789}],
     'l2': [1, 2.0, 'abc', {'def': 789}],
     'm': {'i': 456}}
