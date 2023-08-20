# Simple Groktest exaples

    >>> True
    True

    >>> False
    False

    >>> (1 +
    ...  1)
    2

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
