---
test-type: doctest
test-options: +ELLIPSIS
---

TODO:
 - How to skip tests based on test for PyYAML? This is not possible with
   doctest but we could support front-matter to test. But what's a
   generalized method that doesn't require custom framework mods?

   In Groktest support, we could support an option that indicates the
   remaining tests should be skipped, causing the test to be "skipped".

# Full YAML support

Groktest supports YAML based front matter configuration if PyYAML is
installed. Otherwise Groktest supports a simplistic version of YAML with
only top-level, single line key value assignments.

PyYAML must be installed.

    >>> import yaml

    >>> yaml.__version__
    '6...'

Full YAML front matter parsing is provided by the Groktest function
`_try_parse_full_yaml`.

    >>> import groktest

    >>> def parse_yaml(s: str):
    ...     # Raise error for diagnostics
    ...     pprint(groktest._try_parse_full_yaml(s, "<test>", raise_error=True))

For core front matter parsing tests, see [tests.md](tests.md).

Examples:

    >>> parse_yaml("")
    None

    >>> parse_yaml("""
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
    ... """)
    {'b': True,
     'f': 123.0,
     'i': 123,
     'l1': [1, 2.0, 'abc', {'def': 789}],
     'l2': [1, 2.0, 'abc', {'def': 789}],
     'm': {'i': 456}}

    >>> parse_yaml("""
    ... test-options: +match -case
    ... """)
    {'test-options': '+match -case'}

    >>> parse_yaml("""
    ... test-options: -case
    ... """)
    {'test-options': '-case'}
