---
option-functions: [custom_types]
---

# Custom options

Custom options are defined in [`custom_types.py`](custom_types.py) using
the naming convention `option_xxx`.

The `option_table` function strips repeating table filler char " " and
"-" to support tablular examples that don't match the specific char
counts.

Here's a tabular examples.

    >>> table = """
    ... | Foo | Bar    |
    ... |-----|--------|
    ... | 123 | abcded |
    ... """.strip()

    >>> print(table)
    | Foo | Bar    |
    |-----|--------|
    | 123 | abcded |

If we want use a wildcard match we could end up changing the " " and "-"
char counts used for the table fills.

This example fails because the " " and "-" fill char counts are
different.

    >>> print(table) # +wildcard +fails
    | Foo | Bar  |
    |-----|------|
    | 123 | a... |

We can apply the `table` option to normalize table output so that fill
char counts aren't used in the match.

    >>> print(table) # +wildcard +table
    | Foo | Bar  |
    |-----|------|
    | 123 | a... |
