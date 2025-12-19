---
parse-functions: ["_parse"]
---

# Parse types

Parse types are used with the `+parse` option and expected output.

    >>> print("123")  # +parse
    {i:d}

    >>> assert i == 123

This pattern match fails.

    >>> print("abc")  # +parse +fails
    {i:d}

## Custom types

Use `groktest.parse_type` to define custom parse types.

See `[_parse.py]` for a sample `gretting` parse type.

    >>> print("hello")  # +parse
    {:greeting}

    >>> print("hi")  # +parse
    {:greeting}

This is not a greeting.

    >>> print("bye")  # +parse +fails
    {:greeting}

A parse function validates input and can also coerce a value. See the `parse_uint` function in [`_parse.py`]

    >>> print("123")  # +parse
    {i:uint}

    >>> assert i == 123

    >>> print("-123")  # +parse +fails
    {i:uint}

<!-- Links -->

[`_parse.py`]: ./_parse.py
