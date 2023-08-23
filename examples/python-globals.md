---
test-options: +wildcard
---

# Python Globals

## Built-ins

Python tests have access to the standard set of Python builtins.

    >>> sorted(__builtins__)
    ['ArithmeticError', 'AssertionError', {}, 'zip']

The `__name__` variable is the test file base name.

    >>> __name__
    'python-globals.md'

    >>> __file__  # +paths
    '{}/examples/python-globals.md'

The tests below rely on `python-init` defined in Project config
(`pyproject.toml`). `python-init` is used to initialize the Python
runtime prior to running a test doc.

This is useful when creating test frameworks that use a common set of
functions.

`re` is imported in `python-init`

    >>> re.match(r"Hello (.+)", "Hello Cat")
    <re.Match object; span=(0, 9), match='Hello Cat'>
