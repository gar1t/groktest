---
# test-type is 'default' by default
---

# Default Groktest tests

The default Groktest configuration is based on `doctest`. It uses the
same test definition syntax.

A test is defined using a PS1 of `>>>` followed by a space and then a
Python expression.

    >>> None

    >>> 1
    1

If the evaluated expression is something other than `None`, Groktest
expects the string representation of that value as output. Expected
output must be specified on a line immediately following the test
expression.

    >>> True
    True

If expected output matches the evaluated expression, the test passes,
otherwise it fails. Groktest supports methods for comparing test results
to expected output. By default, output must match exactly. See below for
alternative matching schemes.

    >>> True  # +skip failing test
    true

Test expressions may span multiple lines using PS2.

    >>> (1 +
    ...  1)
    2

If a test expression prints to standard output, that output is included
when comparing expected results.

    >>> print("Hello")
    Hello

If an expression evaluates to non-None and also prints to standard
output, the evaluated result is included after printed output.

    >>> def print_and_return():
    ...     print("a printed str")
    ...     return "a returned str"

    >>> print_and_return()
    a printed str
    'a returned str'

## Blank lines

Groktest requires that expected output contain only non-blank lines. To
represent a blank line in expected output, use a blank line marker. Groktest
uses the token `⤶` (unicode [2936](https://www.compart.com/en/unicode/U+2936))
to represent a blank line. This is equivalent to `<BLANKLINE>` in `doctest`.

    >>> print("")
    ⤶

    >>> print("\n")
    ⤶
    ⤶

    >>> print("foo\n")
    foo
    ⤶

    >>> print("""
    ... foo""")
    ⤶
    foo

    >>> print("""
    ... foo
    ... """)
    ⤶
    foo
    ⤶

    >>> print("""
    ... foo
    ...
    ... bar
    ... """)
    ⤶
    foo
    ⤶
    bar
    ⤶

Blank lines can be disabled using the `blankline` option.

    >>> print("⤶")  # -blankline
    ⤶

The token used to represent blank lines in output can be modified when
enabling the `blankline` option.

    >>> print("⤶\n\n⤶")  # +blankline=<BLANKLINE>
    ⤶
    <BLANKLINE>
    ⤶

    >>> print("")  # +blankline=xxx
    xxx

## Wildcard matching

Wildcard matching is not enabled by default.

    >>> "The sun is strong"  # +fails
    'The ... is strong'

Enable it using the `wildcard` option.

    >>> "The moon hovers"  # +wildcard
    'The ... hovers'

    >>> "The moon hovers"  # +wildcard=*
    'The * hovers'

## Parsing

Expected results can be parsed with pattern matching when `parse` is
enabled.

    >>> "The sun is strong"  # +parse
    'The {} is strong'

Without `parse` this fails.

    >>> "The sun is strong"  # +fails
    'The {} is strong'

Patterns may contain types.

    >>> print("1 + 1 is often 2")  # +parse
    {:d} + {:d} is often {:d}

Matched patterns can be bound to variables.

    >>> print("1 + 1 is often 2")  # +parse
    {x:d} + {y:d} is often {z:d}

    >>> x, y, z
    (1, 1, 2)

    >>> assert x + y == z, (x, y, z)

    >>> assert x + y != z, (x, y, z)
    Traceback (most recent call last):
    AssertionError: (1, 1, 2)

## Case sensitive matching

By default matches are case sensitive.

    >>> print("X")  # +fails
    x

A test can be made case insensitive by disabling `case`.

    >>> print("X")  # -case
    x

This behavior applies when using `parse` matching.

    >>> print("X")  # +parse +fails
    x

    >>> print("X")  # +parse -case
    x
