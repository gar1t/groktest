# White space and tests

White space is checked by default.

    >>> print("a b")  # +fails
    a
    b

White space can be normalized by disabling the `whitespace` option.

    >>> print("a b")  # -whitespace
    a
    b
