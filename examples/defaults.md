---
# test-type is 'default' by default
---

# Default Groktest tests

The default Groktest configuration is based on `doctest`. It uses the
same test definition syntax.

A test is defined using a PS1 of `>>>` followed by a space and then a
Python expression.

    >>> None

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

TODO: Test options

    >> True  # +fails
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
represent a blank line in expected output, use a blank line marker.
Groktest uses the token `|` (pipe character) to represent a blank line.
This is equivalent to `<BLANKLINE>` in `doctest`.

    >>> print("")
    |

    >>> print("\n")
    |
    |

    >>> print("foo\n")
    foo
    |

    >>> print("""
    ... foo""")
    |
    foo

    >>> print("""
    ... foo
    ... """)
    |
    foo
    |

    >>> print("""
    ... foo
    ...
    ... bar
    ... """)
    |
    foo
    |
    bar
    |

To match a literal pipe char on a single line, use the match type
`pipe`.

    >> print("|")  # -blankline
    |

    >> print("|\n\n|")  # +blankline=<BLANKLINE>
    |
    <BLANKLINE>
    |
