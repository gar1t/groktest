# Diff reports

To print a diff between expected and actual test output, use `+diff`.

    >>> print("aaa")  # +diff +fails
    bbb

    >>> print("""a
    ...
    ... b""")  # +diff +fails

    >>> print("""a
    ...
    ... b""")  # +diff +fails
    a
    b

    >>> print("""a
    ... b""")  # +diff +blankline=<empty> +fails
    a
    <empty>
    b
