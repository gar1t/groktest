---
# Unless otherwise specified by `test-type` in this front-matter
# the test type is 'default'
---

    >>> print("")
    |

    >>> print("\n")
    |
    |

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

    >>> True  # +fails  TODO: 1) `-match` by default 2) `fails` option
    true

Test expressions may span multiple lines using PS2.

    >>> (1 +
    ...  1)
    2

If a test expression prints to standard output, that output is included when comparing expected output.

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

As with `doctest`, Groktest requires that expected output contain only
non-empty lines. An empty line signifies the end of the expected output
block. For this reason, blank lines in test result output are encoded
using a non-blank token.

`doctest` uses the token `<BLANKLINE>` to represent a blank line in test
outout.

Groktest uses the token `|` (pipe character).

    >>> print("""
    ... foo
    ... """)
    |
    foo


Use a single pipe (`|`) in place of expected blank lines. This is
equivalent to `<BLANKLINE>` in `doctest`.

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

    >>> print("|")
    {:pipe}
