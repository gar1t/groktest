# Simple Groktest exaples

    >>> True
    True

    >>> False
    False

    >>> (1 +
    ...  1)
    2

Use a single dot (`.`) in place of expected blank lines. This is
equivalent to `<BLANKLINE>` in `doctest`.

    >>> print("foo\n\nbar\n")
    foo
    .
    bar
    .

To match a literal dot on a single line, use the match type `dot`.

    >>> print(".")
    {:dot}
