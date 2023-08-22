---
test-type: doctest
---

Groktest supports [`doctest`](https://docs.python.org/library/doctest)
format.

Test prompts are denoted using `>>>`.

    >>> 1 + 1
    2

Tests don't need to be indented. However, to format examples using fenced blocks in Mardown, tests must be followed by an empty line.

```
>>> 1 + 2
3

```

For this reason Groktest recommends indenting tests in Mardown files.

Errors are tested by providing a `Traceback` example.

    >>> undefined
    Traceback (most recent call last):
    NameError: name 'undefined' is not defined

Testing blank lines.

    >>> print("")
    <BLANKLINE>
